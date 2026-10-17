"""Deliberately vulnerable local API for AccessMatrix demonstrations."""

from itertools import count
from typing import Annotated, Literal

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Response,
    status,
)
from pydantic import (
    BaseModel,
    Field,
)

DemoRole = Literal[
    "customer",
    "admin",
]

InvoiceStatus = Literal[
    "draft",
    "pending",
    "paid",
    "cancelled",
]

CurrencyCode = Literal[
    "AED",
    "EUR",
    "USD",
]


class DemoIdentity(BaseModel):
    """Authenticated identity in the demonstration API."""

    user_id: str
    display_name: str
    role: DemoRole
    tenant_id: str


class Invoice(BaseModel):
    """Invoice record returned by the demonstration API."""

    invoice_id: str
    owner_id: str
    tenant_id: str
    amount: float
    currency: CurrencyCode
    status: InvoiceStatus
    description: str


class InvoiceCreate(BaseModel):
    """Input used to create a demonstration invoice."""

    amount: float = Field(
        gt=0,
        le=1_000_000,
    )

    currency: CurrencyCode = "USD"

    description: str = Field(
        min_length=1,
        max_length=500,
    )


class InvoiceUpdate(BaseModel):
    """Editable invoice fields."""

    amount: float | None = Field(
        default=None,
        gt=0,
        le=1_000_000,
    )

    currency: CurrencyCode | None = None

    status: InvoiceStatus | None = None

    description: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )


class CustomerProfile(BaseModel):
    """Customer profile containing intentionally overexposed properties."""

    customer_id: str
    display_name: str
    tenant_id: str
    email: str
    credit_limit: float
    internal_risk_score: int
    internal_review_notes: str


class AdminReport(BaseModel):
    """Administrative report available only to administrators."""

    customer_count: int
    invoice_count: int
    total_invoice_value: float
    pending_invoice_count: int


def build_seed_invoices() -> dict[str, Invoice]:
    """Create a fresh set of demonstration invoices."""

    return {
        "INV-1001": Invoice(
            invoice_id="INV-1001",
            owner_id="alice",
            tenant_id="tenant-a",
            amount=425.50,
            currency="USD",
            status="paid",
            description=("Alice cloud-services invoice."),
        ),
        "INV-1002": Invoice(
            invoice_id="INV-1002",
            owner_id="alice",
            tenant_id="tenant-a",
            amount=175.00,
            currency="USD",
            status="pending",
            description=("Alice support-services invoice."),
        ),
        "INV-2001": Invoice(
            invoice_id="INV-2001",
            owner_id="bob",
            tenant_id="tenant-b",
            amount=960.25,
            currency="AED",
            status="pending",
            description=("Bob infrastructure invoice."),
        ),
        "INV-2002": Invoice(
            invoice_id="INV-2002",
            owner_id="bob",
            tenant_id="tenant-b",
            amount=310.75,
            currency="AED",
            status="draft",
            description=("Bob security-review invoice."),
        ),
    }


def build_seed_customers() -> dict[str, CustomerProfile]:
    """Create fresh demonstration customer profiles."""

    return {
        "alice": CustomerProfile(
            customer_id="alice",
            display_name="Customer Alice",
            tenant_id="tenant-a",
            email="alice@example.test",
            credit_limit=15_000.00,
            internal_risk_score=18,
            internal_review_notes=("Low-risk demonstration customer."),
        ),
        "bob": CustomerProfile(
            customer_id="bob",
            display_name="Customer Bob",
            tenant_id="tenant-b",
            email="bob@example.test",
            credit_limit=8_000.00,
            internal_risk_score=67,
            internal_review_notes=("Manual review required for high-value transactions."),
        ),
    }


def build_demo_identities() -> dict[str, DemoIdentity]:
    """Map local-only demonstration tokens to identities."""

    return {
        "demo-alice-token": DemoIdentity(
            user_id="alice",
            display_name="Customer Alice",
            role="customer",
            tenant_id="tenant-a",
        ),
        "demo-bob-token": DemoIdentity(
            user_id="bob",
            display_name="Customer Bob",
            role="customer",
            tenant_id="tenant-b",
        ),
        "demo-admin-token": DemoIdentity(
            user_id="admin",
            display_name="Administrator",
            role="admin",
            tenant_id="administration",
        ),
    }


def create_demo_app() -> FastAPI:
    """Create a fresh local demonstration API."""

    application = FastAPI(
        title="AccessMatrix Invoice Demonstration API",
        description=(
            "A local-only API containing controlled "
            "authorization weaknesses for AccessMatrix testing."
        ),
        version="1.0.0",
    )

    identities = build_demo_identities()
    invoices = build_seed_invoices()
    customers = build_seed_customers()
    invoice_sequence = count(3001)

    def require_identity(
        authorization: Annotated[
            str | None,
            Header(
                alias="Authorization",
            ),
        ] = None,
    ) -> DemoIdentity:
        """Authenticate a local demonstration bearer token."""

        if authorization is None:
            raise HTTPException(
                status_code=(status.HTTP_401_UNAUTHORIZED),
                detail=("A Bearer token is required."),
                headers={
                    "WWW-Authenticate": "Bearer",
                },
            )

        scheme, separator, token = authorization.partition(" ")

        if separator != " " or scheme.lower() != "bearer" or not token.strip():
            raise HTTPException(
                status_code=(status.HTTP_401_UNAUTHORIZED),
                detail=("The Authorization header must use the Bearer scheme."),
                headers={
                    "WWW-Authenticate": "Bearer",
                },
            )

        identity = identities.get(token.strip())

        if identity is None:
            raise HTTPException(
                status_code=(status.HTTP_401_UNAUTHORIZED),
                detail=("The demonstration token is invalid."),
                headers={
                    "WWW-Authenticate": "Bearer",
                },
            )

        return identity

    def require_admin(
        identity: Annotated[
            DemoIdentity,
            Depends(require_identity),
        ],
    ) -> DemoIdentity:
        """Require the demonstration administrator role."""

        if identity.role != "admin":
            raise HTTPException(
                status_code=(status.HTTP_403_FORBIDDEN),
                detail=("Administrator access is required."),
            )

        return identity

    def invoice_or_404(
        invoice_id: str,
    ) -> Invoice:
        """Return an invoice or raise a 404 response."""

        invoice = invoices.get(invoice_id)

        if invoice is None:
            raise HTTPException(
                status_code=(status.HTTP_404_NOT_FOUND),
                detail="Invoice not found.",
            )

        return invoice

    @application.get(
        "/health",
        tags=["System"],
    )
    def health() -> dict[str, str]:
        """Return the demonstration service health."""

        return {
            "status": "ok",
            "service": "accessmatrix-demo-api",
        }

    @application.get(
        "/whoami",
        response_model=DemoIdentity,
        tags=["Authentication"],
    )
    def who_am_i(
        identity: Annotated[
            DemoIdentity,
            Depends(require_identity),
        ],
    ) -> DemoIdentity:
        """Return the currently authenticated identity."""

        return identity

    @application.get(
        "/invoices",
        response_model=list[Invoice],
        tags=["Invoices"],
    )
    def list_invoices(
        identity: Annotated[
            DemoIdentity,
            Depends(require_identity),
        ],
    ) -> list[Invoice]:
        """Return invoices visible to the current identity."""

        if identity.role == "admin":
            visible_invoices = list(invoices.values())
        else:
            visible_invoices = [
                invoice for invoice in invoices.values() if (invoice.owner_id == identity.user_id)
            ]

        return sorted(
            visible_invoices,
            key=lambda invoice: invoice.invoice_id,
        )

    @application.get(
        "/invoices/{invoice_id}",
        response_model=Invoice,
        tags=["Invoices"],
    )
    def get_invoice(
        invoice_id: str,
        _: Annotated[
            DemoIdentity,
            Depends(require_identity),
        ],
    ) -> Invoice:
        """Return one invoice.

        This endpoint intentionally omits an ownership check.
        It is the local BOLA demonstration endpoint.
        """

        return invoice_or_404(invoice_id)

    @application.post(
        "/invoices",
        response_model=Invoice,
        status_code=status.HTTP_201_CREATED,
        tags=["Invoices"],
    )
    def create_invoice(
        payload: InvoiceCreate,
        identity: Annotated[
            DemoIdentity,
            Depends(require_identity),
        ],
    ) -> Invoice:
        """Create an invoice for the authenticated identity."""

        if identity.role == "admin":
            raise HTTPException(
                status_code=(status.HTTP_409_CONFLICT),
                detail=("Use a customer identity to create an invoice."),
            )

        invoice_id = f"INV-{next(invoice_sequence)}"

        invoice = Invoice(
            invoice_id=invoice_id,
            owner_id=identity.user_id,
            tenant_id=identity.tenant_id,
            amount=payload.amount,
            currency=payload.currency,
            status="draft",
            description=payload.description,
        )

        invoices[invoice_id] = invoice

        return invoice

    @application.patch(
        "/invoices/{invoice_id}",
        response_model=Invoice,
        tags=["Invoices"],
    )
    def update_invoice(
        invoice_id: str,
        payload: InvoiceUpdate,
        identity: Annotated[
            DemoIdentity,
            Depends(require_identity),
        ],
    ) -> Invoice:
        """Update an owned invoice or any invoice as administrator."""

        invoice = invoice_or_404(invoice_id)

        if identity.role != "admin" and invoice.owner_id != identity.user_id:
            raise HTTPException(
                status_code=(status.HTTP_403_FORBIDDEN),
                detail=("The authenticated identity does not own this invoice."),
            )

        update_values = payload.model_dump(
            exclude_unset=True,
            exclude_none=True,
        )

        updated_invoice = invoice.model_copy(update=update_values)

        invoices[invoice_id] = updated_invoice

        return updated_invoice

    @application.delete(
        "/invoices/{invoice_id}",
        status_code=(status.HTTP_204_NO_CONTENT),
        tags=["Invoices"],
    )
    def delete_invoice(
        invoice_id: str,
        _: Annotated[
            DemoIdentity,
            Depends(require_admin),
        ],
    ) -> Response:
        """Delete an invoice as an administrator."""

        invoice_or_404(invoice_id)

        del invoices[invoice_id]

        return Response(status_code=(status.HTTP_204_NO_CONTENT))

    @application.get(
        "/customers/{customer_id}/profile",
        response_model=CustomerProfile,
        tags=["Customers"],
    )
    def get_customer_profile(
        customer_id: str,
        _: Annotated[
            DemoIdentity,
            Depends(require_identity),
        ],
    ) -> CustomerProfile:
        """Return a customer profile.

        This endpoint intentionally omits owner and tenant checks
        and returns internal properties. It is the local BOPLA
        demonstration endpoint.
        """

        customer = customers.get(customer_id)

        if customer is None:
            raise HTTPException(
                status_code=(status.HTTP_404_NOT_FOUND),
                detail="Customer not found.",
            )

        return customer

    @application.get(
        "/admin/reports",
        response_model=AdminReport,
        tags=["Administration"],
    )
    def get_admin_report(
        _: Annotated[
            DemoIdentity,
            Depends(require_admin),
        ],
    ) -> AdminReport:
        """Return an administrator-only aggregate report."""

        return AdminReport(
            customer_count=len(customers),
            invoice_count=len(invoices),
            total_invoice_value=round(
                sum(invoice.amount for invoice in invoices.values()),
                2,
            ),
            pending_invoice_count=sum(invoice.status == "pending" for invoice in invoices.values()),
        )

    return application


app = create_demo_app()
