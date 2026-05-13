from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend
from django.http import FileResponse
import io

def generate_activity_pdf(activities, context):
    """
    Generates a PDF report for employee daily activities.
    
    Args:
        activities: QuerySet of EmployeeDailyActivity objects
        context: Dictionary containing report metadata (title, employee_name, date_range, etc.)
    
    Returns:
        io.BytesIO buffer containing the PDF
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor("#2c3e50"),
        spaceAfter=12,
        alignment=1  # Center alignment
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor("#7f8c8d"),
        spaceAfter=20,
        alignment=1
    )
    
    header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.white,
        fontName='Helvetica-Bold',
        alignment=1
    )
    
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.black,
        leading=12
    )
    
    # Report Header
    title = context.get('title', 'Employee Activity Report')
    subtitle = f"Employee: {context.get('employee_name', 'All Employees')} | {context.get('date_range', '')}"
    
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(subtitle, subtitle_style))
    
    # Performance Summary Table
    total_activities = len(activities)
    if total_activities > 0:
        from .utils import calculate_performance_metrics
        metrics = calculate_performance_metrics(activities)
        
        avg_progress = metrics['avg_progress']
        avg_target = metrics['avg_target']
        efficiency = metrics['efficiency']
        
        summary_data = [
            [Paragraph("<b>Performance Metrics</b>", header_style), ""],
            ["Avg. Actual Progress", f"{avg_progress:.1f}%"],
            ["Avg. Target Progress", f"{avg_target:.1f}%"],
            ["Progress Efficiency", f"{efficiency:.1f}%"]
        ]
        summary_table = Table(summary_data, colWidths=[60*mm, 35*mm])
        summary_table.setStyle(TableStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor("#34495e")),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        
        # Pull to right
        elements.append(Spacer(1, 5*mm))
        container = Table([[None, summary_table]], colWidths=[75*mm, 95*mm])
        elements.append(container)
        elements.append(Spacer(1, 5*mm))
    
    # Performance Chart
    if len(activities) > 0:
        drawing = Drawing(170*mm, 60*mm)
        bc = VerticalBarChart()
        bc.x = 20
        bc.y = 20
        bc.height = 120
        bc.width = 440
        
        # Data aggregation
        progress_data = []
        target_data = []
        labels = []
        
        # Limit to last 15 activities for chart to keep it readable
        chart_activities = activities[:15]
        # Copy to list for reversing
        chart_list = list(chart_activities)
        chart_list.reverse() # Chronological order
        
        for act in chart_list:
            # Actual Progress
            progress_data.append(100 - (act.pending_work_percentage or 0))
            
            # Target Progress (from previously added logic or new target field)
            # Using act.target_work_percentage if available, otherwise 0
            target_data.append(getattr(act, 'target_work_percentage', 0))
            labels.append(act.date.strftime('%m-%d'))
            
        bc.data = [target_data, progress_data]
        bc.categoryAxis.categoryNames = labels
        bc.categoryAxis.labels.angle = 45
        bc.categoryAxis.labels.dx = 0
        bc.categoryAxis.labels.dy = -10
        bc.categoryAxis.labels.fontSize = 8
        
        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = 100
        bc.valueAxis.valueStep = 20
        
        bc.bars[0].fillColor = colors.HexColor("#bdc3c7") # Target (Light Grey)
        bc.bars[1].fillColor = colors.HexColor("#3498db") # Actual (Blue)
        
        # Legend
        legend = Legend()
        legend.x = 420
        legend.y = 150
        legend.fontSize = 8
        legend.alignment = 'right'
        legend.colorNamePairs = [(colors.HexColor("#bdc3c7"), 'Target %'), (colors.HexColor("#3498db"), 'Actual %')]
        
        drawing.add(bc)
        drawing.add(legend)
        
        elements.append(drawing)
        elements.append(Spacer(1, 10*mm))
    
    elements.append(Spacer(1, 5*mm))
    
    # Table Data
    # Columns: Date, Employee, Project, Role, Team, Description, Status, Target Achieved, Progress
    data = [['Date', 'Employee', 'Project', 'Role', 'Team', 'Description', 'Status', 'Target', 'Progress']]
    
    from .models import ProjectServiceMember, ProjectTeamMember
    
    for activity in activities:
        # Format date
        date_str = activity.date.strftime('%Y-%m-%d')
        
        # Format project name
        project_obj = activity.project
        project_name = (project_obj.name if project_obj else None) or (getattr(activity, 'project_name', None) or "N/A")
        
        # Format Role and Team
        role = str(getattr(activity, 'role', None) or "N/A")
        team_obj = activity.team
        team_name = (team_obj.name if team_obj else None) or "N/A"
        
        # Format description (truncate if too long for PDF cell)
        desc_text = str(activity.description or "")
        description = desc_text[:100] + "..." if len(desc_text) > 100 else desc_text
        
        # Status
        status = "On Time"
        if activity.is_timeline_exceeded:
            status = "Delayed"
            
        # Target Achieved Percentage
        target_achieved_percentage = getattr(activity, 'target_work_percentage', 0)
        target_achieved = f"{target_achieved_percentage}%"

        # Progress (Completed Percentage)
        pending = activity.pending_work_percentage
        completed_percentage = 100 - pending
        progress = f"{completed_percentage}%"
        
        # Employee Info
        employee_name = activity.employee.username if activity.employee else "N/A"
        
        row = [
            Paragraph(date_str, cell_style),
            Paragraph(employee_name, cell_style),
            Paragraph(project_name, cell_style),
            Paragraph(role, cell_style),
            Paragraph(team_name, cell_style),
            Paragraph(description, cell_style),
            Paragraph(status, cell_style),
            Paragraph(target_achieved, cell_style),
            Paragraph(progress, cell_style)
        ]
        data.append(row)
        
    # Table Styling
    # Total available width = 170mm
    # Date(18), Emp(20), Proj(20), Role(18), Team(18), Desc(32), Status(15), Target(14), Prog(15)
    col_widths = [18*mm, 20*mm, 20*mm, 18*mm, 18*mm, 32*mm, 15*mm, 14*mm, 15*mm]
    table = Table(data, colWidths=col_widths)
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#34495e")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9), # Slightly smaller font for headers
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8f9fa")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 1), (1, -1), 'CENTER'), # Center Date and Employee
        ('ALIGN', (6, 1), (8, -1), 'CENTER'), # Center Status, Target, Progress
    ]))
    
    elements.append(table)
    
    # Summary Footer
    elements.append(Spacer(1, 10*mm))
    summary_text = f"Total Activities Logged: {len(activities)}"
    elements.append(Paragraph(summary_text, subtitle_style))
    
    doc.build(elements)
    buffer.seek(0)
    
    return buffer

def generate_invoice_pdf(invoice):
    """
    Generates a PDF for an invoice matching the ex media template.
    """
    from .models import CompanyProfile
    from reportlab.platypus import Image, Spacer, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate
    import os
    from django.conf import settings
    import io

    # Colors
    TEXT_MAIN = colors.HexColor("#000000")
    TEXT_MUTED = colors.HexColor("#4a4a4a")
    LIGHT_GREY = colors.HexColor("#EAEAEA")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=5*mm,
        bottomMargin=10*mm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    company = CompanyProfile.objects.first()

    # --- Header ---
    logo_img = ""
    if company and company.logo:
        logo_path = os.path.join(settings.MEDIA_ROOT, str(company.logo))
        if os.path.exists(logo_path):
            logo_img = Image(logo_path, width=45*mm, height=22*mm, kind='proportional')

    right_header = Paragraph(
        "I N V O I C E", 
        ParagraphStyle('InvTitle', fontName='Helvetica', fontSize=26, textColor=colors.HexColor("#666666"), alignment=2)
    )
    
    header_table = Table([[logo_img, right_header]], colWidths=[90*mm, 90*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5*mm),
    ]))
    elements.append(header_table)
    
    # --- Detail Cards (FROM and BILL TO) ---
    meta_val = ParagraphStyle('MetaVal', fontSize=9, textColor=TEXT_MAIN, leading=12)
    
    # LEFT: BILL TO
    client = invoice.client_company
    client_name = client.legal_name if client else "N/A"
    address_parts = []
    if client:
        parts = [client.unit_or_floor, client.building_name, client.street_name, client.city]
        address_parts = [p.strip() for p in parts if p and p.strip()]
        state_pin = ""
        if client.state and client.state.strip():
            state_pin = client.state.strip()
            if client.pin_code and client.pin_code.strip():
                state_pin += f" - {client.pin_code.strip()}"
        elif client.pin_code and client.pin_code.strip():
            state_pin = client.pin_code.strip()
        if state_pin:
            address_parts.append(state_pin)
    client_address = ", ".join(address_parts)
    
    client_info_lines = [f"{client_name}"]
    if client_address: client_info_lines.append(client_address)
    client_info_html = "<br/>".join(client_info_lines)
    
    left_table = Table([
        [Paragraph("<font size='8'>BILL TO</font>", meta_val), ""],
        ["", Paragraph(client_info_html, meta_val)]
    ], colWidths=[18*mm, 72*mm])
    left_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (1,0), -4), # Slight negative padding to pull them closer
    ]))
    
    left_block = left_table

    # RIGHT: Invoice Meta Block
    inv_date_str = invoice.invoice_date.strftime('%d - %m - %Y') if invoice.invoice_date else "N/A"
    due_date_str = invoice.due_date.strftime('%d - %m - %Y') if invoice.due_date else "N/A"
    inv_num_str = f"<b>{invoice.invoice_number or 'N/A'}</b>"
    
    meta_table_style = ParagraphStyle('MT', fontSize=9, leading=12)
    
    rt_data = [
        [Paragraph("Invoice Number", meta_table_style), Paragraph(":", meta_table_style), Paragraph(inv_num_str, meta_table_style)],
        [Paragraph("Invoice Date", meta_table_style), Paragraph(":", meta_table_style), Paragraph(inv_date_str, meta_table_style)],
        [Paragraph("Payment Due", meta_table_style), Paragraph(":", meta_table_style), Paragraph(due_date_str, meta_table_style)],
        [Paragraph("Amount Due (INR)", meta_table_style), Paragraph(":", meta_table_style), Paragraph(f"<b>{invoice.balance_due:,.2f}</b>", meta_table_style)],
    ]
    right_table = Table(rt_data, colWidths=[30*mm, 5*mm, 40*mm])
    right_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ('BACKGROUND', (0,3), (-1,3), LIGHT_GREY), # Shaded Amount Due Row
    ]))

    info_table = Table([[left_block, right_table]], colWidths=[90*mm, 90*mm])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8*mm),
    ]))
    elements.append(info_table)
    
    # --- Items Table ---
    header_data = ['Service / Item', 'Description', 'Period', 'Rate', 'Qty', 'Total']
    data = [[Paragraph(h, ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=9, alignment=1)) for h in header_data]]
    
    item_count = 0
    for item in invoice.items.all():
        item_count += 1
        period_str = ""
        if item.purchase_date and item.expairy_date:
            period_str = f"{item.purchase_date.strftime('%y/%m/%d')} - {item.expairy_date.strftime('%y/%m/%d')}"
            
        data.append([
            Paragraph(str(item.service_type or "N/A"), ParagraphStyle('TC', alignment=1, fontSize=9)),
            Paragraph(str(item.description or ""), ParagraphStyle('TCDesc', alignment=1, fontSize=8, textColor=TEXT_MUTED)),
            Paragraph(period_str, ParagraphStyle('TCPer', alignment=1, fontSize=8, textColor=TEXT_MUTED)),
            Paragraph(f"{item.rate:,.2f}", ParagraphStyle('TCRate', alignment=1, fontSize=9)),
            Paragraph(str(item.quantity), ParagraphStyle('TCQty', alignment=1, fontSize=9)),
            Paragraph(f"{item.total_price:,.2f}", ParagraphStyle('TCTot', alignment=1, fontSize=9))
        ])
        
    # Pad items to create vertical lines going down to the totals area
    MIN_ROWS = 8
    rows_to_pad = max(0, MIN_ROWS - item_count)
    for _ in range(rows_to_pad):
        data.append(["", "", "", "", "", ""])
        
    col_widths = [30*mm, 45*mm, 35*mm, 20*mm, 15*mm, 35*mm] # total 180mm
    table = Table(data, colWidths=col_widths)
    
    ts = [
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GREY),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4*mm),
        ('TOPPADDING', (0, 1), (-1, -1), 4*mm),
    ]
    
    # Inner vertical lines starting from below the header
    for col in range(1, len(header_data)):
        ts.append(('LINEBEFORE', (col, 1), (col, -1), 0.5, TEXT_MUTED))
        
    table.setStyle(TableStyle(ts))
    elements.append(table)
    
    # Bottom Horizontal line
    line_table = Table([['']], colWidths=[180*mm])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 0.5, TEXT_MAIN),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(line_table)
    
    # --- Bottom Area ---
    # Left: Bank Details
    bank_lines = [Paragraph("<i>Bank Details</i>", ParagraphStyle('BI', fontSize=8, textColor=TEXT_MUTED))]
    bank_lines.append(Paragraph("_" * 30, ParagraphStyle('BL', fontSize=8, textColor=TEXT_MUTED)))
    
    b_style = ParagraphStyle('BV', fontSize=8, leading=10, fontName='Helvetica-Bold')
    n_style = ParagraphStyle('BN', fontSize=8, leading=10)
    company_name = company.company_name if company else "Extechnology"
    bank_lines.append(Paragraph(company_name.upper(), b_style))
    if company and company.account_number: bank_lines.append(Paragraph(f"A/c NO. {company.account_number}", n_style))
    if company and company.bank_name: bank_lines.append(Paragraph(company.bank_name.upper(), b_style))
    if company and company.ifsc_code: bank_lines.append(Paragraph(f"IFSC: <b>{company.ifsc_code}</b>", n_style))
    
    # Right: Totals
    t_lbl = ParagraphStyle('TLbl', fontSize=9, alignment=2)
    t_val = ParagraphStyle('TVal', fontSize=9, alignment=2)
    t_val_bold = ParagraphStyle('TValB', fontSize=9, fontName='Helvetica-Bold', alignment=2)

    totals_data = [
        [Paragraph("Total", t_lbl), Paragraph(":", t_lbl), Paragraph(f"{invoice.subtotal:,.2f}", t_val_bold)],
    ]
    if invoice.tax_amount > 0:
        totals_data.append([Paragraph(f"Tax ({invoice.tax_rate}%)", t_lbl), Paragraph(":", t_lbl), Paragraph(f"{invoice.tax_amount:,.2f}", t_val_bold)])
    if invoice.discount_amount > 0:
        totals_data.append([Paragraph("Discount", t_lbl), Paragraph(":", t_lbl), Paragraph(f"-{invoice.discount_amount:,.2f}", t_val_bold)])
        
    totals_data.append([Paragraph("Advance", t_lbl), Paragraph(":", t_lbl), Paragraph(f"{invoice.total_paid:,.2f}" if invoice.total_paid else "", t_val)])
    totals_data.append([Paragraph("Amount Due (INR)", t_lbl), Paragraph(":", t_lbl), Paragraph(f"{invoice.balance_due:,.2f}", t_val_bold)])
    
    totals_table = Table(totals_data, colWidths=[40*mm, 5*mm, 25*mm])
    tt_style = [
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LINEABOVE', (0,-1), (-1,-1), 0.5, TEXT_MAIN),
        ('LINEBELOW', (0,-1), (-1,-1), 0.5, TEXT_MAIN),
    ]
    totals_table.setStyle(TableStyle(tt_style))

    bank_container = Table([[p] for p in bank_lines], colWidths=[80*mm])
    bank_container.setStyle(TableStyle([('LEFTPADDING', (0,0), (-1,-1), 5*mm), ('BOTTOMPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0)]))

    bottom_container = Table([[bank_container, totals_table]], colWidths=[100*mm, 80*mm])
    bottom_container.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('TOPPADDING', (0,0), (-1,-1), 4*mm)]))
    elements.append(bottom_container)
    
    # --- Footer Line ---
    elements.append(Spacer(1, 4*mm))
    
    footer_text = []
    if company and company.address:
        footer_text.append(f"<font name='ZapfDingbats'>&#x27A4;</font> {company.address}") # Arrow for address
    if company and company.phone:
        footer_text.append(f"<font name='ZapfDingbats'>&#x2706;</font> {company.phone}") # Phone icon
    if company and company.email:
        footer_text.append(f"<font name='ZapfDingbats'>&#x2709;</font> {company.email}") # Envelope icon
        
    footer_str = " | ".join(footer_text)
    
    f_style = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontSize=7,
        textColor=TEXT_MUTED,
        alignment=1 
    )
    elements.append(Paragraph(footer_str, f_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
def _create_financial_pdf_base(title, data_sections, context, total_text, total_val):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor("#2c3e50"), spaceAfter=12, alignment=1
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#7f8c8d"), spaceAfter=20, alignment=1
    )
    cell_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=10, textColor=colors.black, leading=14)
    bold_style = ParagraphStyle('TableBold', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', textColor=colors.black, leading=14)

    elements.append(Paragraph(f"<b>{title}</b>", title_style))
    
    start_date = context.get('start_date')
    end_date = context.get('end_date')
    month = context.get('month')
    year = context.get('year')
    
    date_str = ""
    if start_date and end_date:
        date_str = f"Period: {start_date} to {end_date}"
    elif month and year:
        date_str = f"Period: {year}-{month}"
    elif year:
        date_str = f"Year: {year}"
    elif end_date:
        date_str = f"As of: {end_date}"
    
    if date_str:
        elements.append(Paragraph(date_str, subtitle_style))
        
    table_data = []
    
    for section_title, rows, sec_total_text, sec_total_val in data_sections:
        table_data.append([Paragraph(f"<b>{section_title}</b>", bold_style), ""])
        for label, val in rows:
            formatted_val = f"{float(val):,.2f}" if val is not None else "0.00"
            table_data.append([Paragraph(label, cell_style), formatted_val])
        
        formatted_sec_total = f"{float(sec_total_val):,.2f}" if sec_total_val is not None else "0.00"
        table_data.append([Paragraph(f"<b>{sec_total_text}</b>", bold_style), formatted_sec_total])
        table_data.append(["", ""]) # spacer

    formatted_total = f"{float(total_val):,.2f}" if total_val is not None else "0.00"
    table_data.append([Paragraph(f"<b>{total_text}</b>", bold_style), formatted_total])

    table = Table(table_data, colWidths=[120*mm, 50*mm])
    table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.black), # Line above final total
    ]))
    
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_income_statement_pdf(data, context):
    revenue = data['revenue']
    expenses = data['expenses']
    net_income = data['net_income']
    
    sections = [
        ("Revenue", [
            ("Invoices Revenue", revenue['invoices']),
            ("Other Income", revenue['other_income'])
        ], "Total Revenue", revenue['total_revenue']),
        ("Expenses", [
            ("Salaries", expenses['salaries']),
            ("Other Expenses", expenses['other_expenses']),
            ("Domains and Servers", expenses['domains_and_servers'])
        ], "Total Expenses", expenses['total_expenses'])
    ]
    
    return _create_financial_pdf_base("INCOME STATEMENT", sections, context, "Net Income", net_income)

def generate_cash_flow_statement_pdf(data, context):
    cash_in = data['cash_in']
    cash_out = data['cash_out']
    net_flow = data['net_cash_flow']
    
    sections = [
        ("Cash Inflows", [
            ("Invoice Payments Received", cash_in['invoice_payments']),
            ("Other Income Received", cash_in['other_income']),
            ("Client Advances Received", cash_in['client_advances'])
        ], "Total Cash Inflows", cash_in['total_cash_in']),
        ("Cash Outflows", [
            ("Salaries Paid", cash_out['salaries_paid']),
            ("Other Expenses Paid", cash_out['other_expenses']),
            ("Domains & Servers Paid", cash_out['domains_servers_paid'])
        ], "Total Cash Outflows", cash_out['total_cash_out'])
    ]
    
    return _create_financial_pdf_base("CASH FLOW STATEMENT", sections, context, "Net Cash Flow", net_flow)

def generate_balance_sheet_pdf(data, context):
    assets = data['assets']
    liabilities = data['liabilities']
    equity = data['equity']
    
    sections = [
        ("Assets", [
            ("Cash and Equivalents", assets['cash_on_hand']),
            ("Accounts Receivable", assets['accounts_receivable'])
        ], "Total Assets", assets['total_assets']),
        ("Liabilities", [
            ("Accounts Payable", liabilities['accounts_payable']),
            ("Client Advances (Unearned Revenue)", liabilities['client_advances'])
        ], "Total Liabilities", liabilities['total_liabilities']),
        ("Equity", [
            ("Retained Earnings", equity['retained_earnings'])
        ], "Total Equity", equity['total_equity'])
    ]
    
    # Check accounting equation
    return _create_financial_pdf_base("BALANCE SHEET", sections, context, "Total Liabilities & Equity", liabilities['total_liabilities'] + equity['total_equity'])


