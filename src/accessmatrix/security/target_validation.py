"""DNS and IP validation for controlled target access."""

import ipaddress
import socket
from concurrent.futures import (
    ThreadPoolExecutor,
)
from concurrent.futures import (
    TimeoutError as FutureTimeoutError,
)
from typing import Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    Field,
)

from accessmatrix.settings.models import (
    NetworkSafetySettings,
)

AddressClassification = Literal[
    "global",
    "loopback",
    "private",
    "link_local",
    "multicast",
    "reserved",
    "unspecified",
]


class ResolvedTargetAddress(BaseModel):
    """One resolved target IP address."""

    address: str
    classification: AddressClassification
    permitted: bool


class TargetValidationResult(BaseModel):
    """Target URL validation and policy result."""

    original_url: str
    normalized_url: str | None

    scheme: str | None
    hostname: str | None
    port: int | None

    valid: bool
    permitted: bool

    resolution_performed: bool
    dns_pin_recommended: bool

    addresses: list[ResolvedTargetAddress] = Field(
        default_factory=list,
    )

    issues: list[str] = Field(
        default_factory=list,
    )

    policy_violations: list[str] = Field(
        default_factory=list,
    )


def classify_ip_address(
    address: (ipaddress.IPv4Address | ipaddress.IPv6Address),
) -> AddressClassification:
    """Classify one resolved IP address."""

    if address.is_unspecified:
        return "unspecified"

    if address.is_multicast:
        return "multicast"

    if address.is_loopback:
        return "loopback"

    if address.is_link_local:
        return "link_local"

    if address.is_private:
        return "private"

    if address.is_reserved:
        return "reserved"

    return "global"


def address_is_permitted(
    classification: AddressClassification,
    settings: NetworkSafetySettings,
) -> bool:
    """Return whether an address class is allowed."""

    if classification == "global":
        return True

    if classification == "loopback":
        return settings.access_mode in {
            "public_and_loopback",
            "private_networks",
        }

    if classification == "private":
        return settings.access_mode == "private_networks"

    if classification == "link_local":
        return settings.access_mode == "private_networks" and settings.allow_link_local

    if classification == "multicast":
        return settings.allow_multicast

    if classification == "reserved":
        return settings.allow_reserved

    return False


def resolve_hostname(
    hostname: str,
    port: int,
    *,
    timeout_seconds: float,
) -> list[str]:
    """Resolve a hostname with a bounded wait."""

    def perform_resolution() -> list[str]:
        results = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )

        return [str(result[4][0]) for result in results]

    worker = ThreadPoolExecutor(max_workers=1)

    future = worker.submit(perform_resolution)

    try:
        return future.result(timeout=timeout_seconds)

    except FutureTimeoutError as exc:
        future.cancel()

        raise TimeoutError("DNS resolution exceeded the configured timeout.") from exc

    finally:
        worker.shutdown(
            wait=False,
            cancel_futures=True,
        )


def validate_target_url(
    url: str,
    *,
    settings: NetworkSafetySettings,
) -> TargetValidationResult:
    """Validate a target URL against network-access policy."""

    original_url = url
    normalized_input = url.strip()

    issues: list[str] = []
    policy_violations: list[str] = []

    if not normalized_input:
        return TargetValidationResult(
            original_url=original_url,
            normalized_url=None,
            scheme=None,
            hostname=None,
            port=None,
            valid=False,
            permitted=False,
            resolution_performed=False,
            dns_pin_recommended=False,
            issues=["The target URL is empty."],
        )

    try:
        parsed = urlsplit(normalized_input)

    except ValueError as exc:
        return TargetValidationResult(
            original_url=original_url,
            normalized_url=None,
            scheme=None,
            hostname=None,
            port=None,
            valid=False,
            permitted=False,
            resolution_performed=False,
            dns_pin_recommended=False,
            issues=[(f"The target URL could not be parsed: {exc}")],
        )

    scheme = parsed.scheme.lower()

    if scheme not in {
        "http",
        "https",
    }:
        issues.append("Only HTTP and HTTPS target URLs are supported.")

    if parsed.username is not None or parsed.password is not None:
        issues.append("Target URLs must not contain embedded credentials.")

    if parsed.query:
        issues.append("Target base URLs must not contain a query string.")

    if parsed.fragment:
        issues.append("Target base URLs must not contain a fragment.")

    hostname = parsed.hostname

    if not hostname:
        issues.append("The target URL must contain a hostname.")

    try:
        parsed_port = parsed.port

    except ValueError as exc:
        issues.append(f"The target port is invalid: {exc}")

        parsed_port = None

    port = parsed_port if parsed_port is not None else (443 if scheme == "https" else 80)

    if issues or hostname is None:
        return TargetValidationResult(
            original_url=original_url,
            normalized_url=(normalized_input),
            scheme=scheme or None,
            hostname=hostname,
            port=port,
            valid=False,
            permitted=False,
            resolution_performed=False,
            dns_pin_recommended=False,
            issues=issues,
        )

    raw_addresses: list[str] = []
    resolution_performed = False
    hostname_is_literal = False

    try:
        literal_address = ipaddress.ip_address(hostname)

        raw_addresses = [str(literal_address)]

        hostname_is_literal = True

    except ValueError:
        if not settings.resolve_hostnames:
            issues.append(
                "Hostname resolution is disabled, so this hostname cannot be safely classified."
            )

        else:
            try:
                raw_addresses = resolve_hostname(
                    hostname,
                    port,
                    timeout_seconds=(settings.dns_resolution_timeout_seconds),
                )

                resolution_performed = True

            except (
                OSError,
                TimeoutError,
            ) as exc:
                issues.append(f"The target hostname could not be resolved: {exc}")

    unique_addresses = sorted(set(raw_addresses))

    if len(unique_addresses) > settings.max_resolved_addresses:
        issues.append("The hostname resolved to more addresses than the configured safety limit.")

        unique_addresses = unique_addresses[: settings.max_resolved_addresses]

    resolved_addresses: list[ResolvedTargetAddress] = []

    for raw_address in unique_addresses:
        try:
            parsed_address = ipaddress.ip_address(raw_address)

        except ValueError:
            issues.append(f"DNS returned an invalid IP address: {raw_address}")

            continue

        classification = classify_ip_address(parsed_address)

        permitted = address_is_permitted(
            classification,
            settings,
        )

        resolved_addresses.append(
            ResolvedTargetAddress(
                address=str(parsed_address),
                classification=(classification),
                permitted=permitted,
            )
        )

        if not permitted:
            policy_violations.append(
                f"Address {parsed_address} is classified "
                f"as {classification} and is not allowed "
                "by the current network-access policy."
            )

    if not resolved_addresses:
        issues.append("The target did not produce any usable IP addresses.")

    valid = not issues

    permitted = valid and not policy_violations and bool(resolved_addresses)

    return TargetValidationResult(
        original_url=original_url,
        normalized_url=normalized_input,
        scheme=scheme,
        hostname=hostname,
        port=port,
        valid=valid,
        permitted=permitted,
        resolution_performed=(resolution_performed),
        dns_pin_recommended=(resolution_performed and not hostname_is_literal),
        addresses=resolved_addresses,
        issues=issues,
        policy_violations=(policy_violations),
    )
