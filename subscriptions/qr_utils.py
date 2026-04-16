"""QR code generation for VPN subscription links."""

import io

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False


def generate_qr_code(data):
    """Generate QR code as PNG bytes in memory.

    Returns BytesIO with PNG data, or None if qrcode library not installed.
    """
    if not HAS_QRCODE:
        return None

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color='#0a1a1f', back_color='#e0f0f0')

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf
