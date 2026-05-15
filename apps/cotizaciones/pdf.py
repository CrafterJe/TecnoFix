"""
Generación de PDFs para cotizaciones con ReportLab.

Dos variantes:
- Cliente: lo que se entrega al cliente (sin info de fuente/origen).
- Empresa: uso interno (con fuente, link y precio base).
"""
from decimal import Decimal
from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PRIMARY = colors.HexColor('#1E3A8A')
ACCENT = colors.HexColor('#3B82F6')
LIGHT = colors.HexColor('#EFF6FF')
MUTED = colors.HexColor('#64748B')


def _estilos():
    base = getSampleStyleSheet()
    return {
        'titulo': ParagraphStyle(
            'titulo', parent=base['Heading1'],
            fontSize=22, textColor=PRIMARY, spaceAfter=4,
        ),
        'subtitulo': ParagraphStyle(
            'subtitulo', parent=base['Normal'],
            fontSize=11, textColor=MUTED, spaceAfter=14,
        ),
        'h2': ParagraphStyle(
            'h2', parent=base['Heading2'],
            fontSize=13, textColor=PRIMARY, spaceBefore=10, spaceAfter=6,
        ),
        'normal': base['Normal'],
        'small': ParagraphStyle(
            'small', parent=base['Normal'],
            fontSize=8, textColor=MUTED, alignment=1,
        ),
        'celda': ParagraphStyle(
            'celda', parent=base['Normal'], fontSize=9,
        ),
    }


def _encabezado(cot, variante: str, estilos):
    titulo = Paragraph(
        f'<b>Cotización {cot.numero_cotizacion}</b>',
        estilos['titulo'],
    )
    fecha = timezone.localtime(cot.created_at).strftime('%d/%m/%Y %H:%M')
    sub = Paragraph(
        f'Generada: {fecha} &nbsp;|&nbsp; Estado: {cot.get_estado_display()}'
        f' &nbsp;|&nbsp; Versión: {variante}',
        estilos['subtitulo'],
    )
    return [titulo, sub]


def _datos_cliente(cot, estilos):
    cliente_info = cot.nombre_cliente
    if cot.cliente_id:
        cliente_info += f' (registrado #{cot.cliente_id})'

    data = [
        [Paragraph('<b>Cliente</b>', estilos['celda']),
         Paragraph(cliente_info, estilos['celda'])],
        [Paragraph('<b>Generada por</b>', estilos['celda']),
         Paragraph(
             cot.created_by.nombre if cot.created_by else '—',
             estilos['celda']
         )],
    ]
    tabla = Table(data, colWidths=[4 * cm, 13 * cm])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LIGHT),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return tabla


def _tabla_items_cliente(cot, estilos):
    headers = ['#', 'Concepto', 'Cantidad', 'Precio unitario', 'Subtotal']
    rows = [headers]
    total = Decimal('0')

    for i, item in enumerate(cot.items.all(), start=1):
        concepto = item.tipo_reparacion.nombre
        if item.subcategoria:
            concepto += f' — {item.subcategoria.nombre}'
        if item.producto_titulo:
            concepto += f'\n{item.producto_titulo}'

        subtotal = item.precio_final * item.cantidad
        total += subtotal

        rows.append([
            str(i),
            Paragraph(concepto.replace('\n', '<br/>'), estilos['celda']),
            str(item.cantidad),
            f'${item.precio_final:,.2f}',
            f'${subtotal:,.2f}',
        ])

    rows.append(['', '', '', Paragraph('<b>TOTAL</b>', estilos['celda']),
                 Paragraph(f'<b>${total:,.2f}</b>', estilos['celda'])])

    tabla = Table(rows, colWidths=[0.8 * cm, 8.5 * cm, 2.2 * cm, 3 * cm, 3 * cm])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, LIGHT]),
        ('BACKGROUND', (0, -1), (-1, -1), PRIMARY),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return tabla


def _tabla_items_empresa(cot, estilos):
    headers = [
        '#', 'Reparación', 'Producto', 'Fuente',
        'Precio base', 'Fórmula', 'Precio final', 'Disp.', 'Cant.',
    ]
    rows = [headers]
    total = Decimal('0')

    for i, item in enumerate(cot.items.all(), start=1):
        concepto = item.tipo_reparacion.nombre
        if item.subcategoria:
            concepto += f' / {item.subcategoria.nombre}'

        producto = item.producto_titulo or '—'
        if item.link_referencia:
            producto += f'\n{item.link_referencia}'

        if item.es_manual:
            fuente_label = 'Manual'
        elif item.fuente_api:
            fuente_label = item.fuente_api.nombre
        else:
            fuente_label = '—'

        subtotal = item.precio_final * item.cantidad
        total += subtotal

        rows.append([
            str(i),
            Paragraph(concepto, estilos['celda']),
            Paragraph(producto.replace('\n', '<br/>'), estilos['celda']),
            fuente_label,
            f'${item.precio_base:,.2f}',
            item.formula_snapshot or '—',
            f'${item.precio_final:,.2f}',
            'Sí' if item.disponible else 'No',
            str(item.cantidad),
        ])

    rows.append([
        '', '', '', '', '', '',
        Paragraph(f'<b>TOTAL: ${total:,.2f}</b>', estilos['celda']),
        '', '',
    ])

    tabla = Table(
        rows,
        colWidths=[
            0.7 * cm, 2.8 * cm, 4.2 * cm, 1.8 * cm,
            1.8 * cm, 2 * cm, 2 * cm, 1 * cm, 1 * cm,
        ],
    )
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (4, 1), (6, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, LIGHT]),
        ('BACKGROUND', (0, -1), (-1, -1), ACCENT),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('SPAN', (0, -1), (5, -1)),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    return tabla


def _pie(estilos):
    return Paragraph(
        'TecnoFix — Documento generado automáticamente. '
        'Esta cotización tiene vigencia de 15 días.',
        estilos['small'],
    )


def _construir_pdf(cot, variante: str, tabla_items, incluir_notas: bool) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f'Cotización {cot.numero_cotizacion}',
        author='TecnoFix',
    )

    estilos = _estilos()
    story = []
    story.extend(_encabezado(cot, variante, estilos))
    story.append(_datos_cliente(cot, estilos))
    story.append(Spacer(1, 12))
    story.append(Paragraph('Conceptos cotizados', estilos['h2']))
    story.append(tabla_items)

    if incluir_notas and cot.notas:
        story.append(Spacer(1, 12))
        story.append(Paragraph('Notas', estilos['h2']))
        story.append(Paragraph(
            cot.notas.replace('\n', '<br/>'),
            estilos['normal'],
        ))

    story.append(Spacer(1, 18))
    story.append(_pie(estilos))

    doc.build(story)
    buffer.seek(0)
    return buffer


def generar_pdf_cliente(cot) -> BytesIO:
    """PDF apto para entregar al cliente: sin fuente, sin link, sin fórmula."""
    estilos = _estilos()
    return _construir_pdf(
        cot,
        variante='Cliente',
        tabla_items=_tabla_items_cliente(cot, estilos),
        incluir_notas=True,
    )


def generar_pdf_empresa(cot) -> BytesIO:
    """PDF interno: incluye fuente, precio base, fórmula y link de referencia."""
    estilos = _estilos()
    return _construir_pdf(
        cot,
        variante='Empresa',
        tabla_items=_tabla_items_empresa(cot, estilos),
        incluir_notas=True,
    )
