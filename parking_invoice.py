"""Módulo de Facturación Electrónica Siigo para Parqueadero."""

from datetime import datetime
from typing import Any, Dict

from config import SIIGO_ACCESS_KEY, SIIGO_APP_NAME, SIIGO_USERNAME
from siigo_client import SiigoClient

SIIGO_CONFIG = {
    "document_type_id": None,
    "seller_id": None,
    "payment_type_id": None,
    "tax_id": None,
}

ITEM_PARQUEADERO = {
    "code": "PARQUEADERO",
    "description": "Servicio de Parqueadero"
}


def emit_electronic_invoice(
    *,
    placa: str,
    id_number: str,
    full_name: str,
    email: str,
    total_amount_cop: int,
) -> Dict[str, Any]:
    """
    Crea factura electrónica en Siigo para servicio de parqueadero.

    Args:
        placa: Placa del vehículo
        id_number: NIT o cédula del cliente
        full_name: Nombre o razón social
        email: Correo electrónico
        total_amount_cop: Monto total en COP

    Retorna la respuesta de Siigo con la factura creada.
    """
    placa = (placa or "").strip().upper()
    id_number = (id_number or "").strip()
    full_name = (full_name or "").strip()
    email = (email or "").strip()
    total_amount_cop = int(total_amount_cop or 0)

    if not placa:
        raise ValueError("Factura electrónica requiere placa del vehículo")
    if not id_number:
        raise ValueError("Factura electrónica requiere NIT o cédula")
    if not full_name:
        raise ValueError("Factura electrónica requiere nombre o razón social")
    if not email:
        raise ValueError("Factura electrónica requiere correo electrónico")
    if total_amount_cop <= 0:
        raise ValueError("Monto total inválido para facturación")

    _validar_config()

    client = SiigoClient(
        username=SIIGO_USERNAME,
        access_key=SIIGO_ACCESS_KEY,
        application_name=SIIGO_APP_NAME
    )

    today = datetime.now().strftime("%Y-%m-%d")

    invoice_data = {
        "document": {"id": SIIGO_CONFIG["document_type_id"]},
        "date": today,
        "customer": {
            "identification": id_number,
            "branch_office": 0
        },
        "seller": SIIGO_CONFIG["seller_id"],
        "items": [{
            "code": ITEM_PARQUEADERO["code"],
            "description": ITEM_PARQUEADERO["description"],
            "quantity": 1,
            "price": total_amount_cop,
            "discount": 0,
            "taxes": [{"id": SIIGO_CONFIG["tax_id"]}] if SIIGO_CONFIG["tax_id"] else []
        }],
        "payments": [{
            "id": SIIGO_CONFIG["payment_type_id"],
            "value": total_amount_cop,
            "due_date": today
        }],
        "observations": f"Placa: {placa} - Cliente: {full_name}"
    }

    result = client.create_invoice(invoice_data)

    if email:
        try:
            client.send_invoice_email(result["id"], email)
        except Exception:
            pass

    return result


def _validar_config() -> None:
    required = ["document_type_id", "seller_id", "payment_type_id"]
    missing = [k for k in required if not SIIGO_CONFIG.get(k)]
    if missing:
        raise ValueError(f"Faltan IDs de configuración: {missing}. Ejecuta get_siigo_ids() para obtenerlos.")


def configurar_siigo(document_type_id: int, seller_id: int, payment_type_id: int, tax_id: int = None) -> None:
    SIIGO_CONFIG["document_type_id"] = document_type_id
    SIIGO_CONFIG["seller_id"] = seller_id
    SIIGO_CONFIG["payment_type_id"] = payment_type_id
    if tax_id:
        SIIGO_CONFIG["tax_id"] = tax_id


def get_siigo_ids() -> None:
    client = SiigoClient(
        username=SIIGO_USERNAME,
        access_key=SIIGO_ACCESS_KEY,
        application_name=SIIGO_APP_NAME
    )

    print("IDs DE CONFIGURACIÓN SIIGO")
    print("=" * 40)

    try:
        print("\nTipos de Documento:")
        for dt in client.get_document_types():
            print(f"  ID: {dt.get('id')} - {dt.get('name')}")
    except Exception as e:
        print(f"  Error: {e}")

    try:
        print("\nMétodos de Pago:")
        for pt in client.get_payment_types():
            print(f"  ID: {pt.get('id')} - {pt.get('name')}")
    except Exception as e:
        print(f"  Error: {e}")

    try:
        print("\nImpuestos:")
        for tax in client.get_taxes():
            print(f"  ID: {tax.get('id')} - {tax.get('name')} ({tax.get('percentage')}%)")
    except Exception as e:
        print(f"  Error: {e}")

    try:
        print("\nVendedores:")
        for s in client.get_sellers():
            print(f"  ID: {s.get('id')} - {s.get('first_name')} {s.get('last_name')}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n" + "=" * 40)
    print("Usa estos IDs con configurar_siigo()")
