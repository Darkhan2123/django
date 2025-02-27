from django.template.loader import render_to_string
from weasyprint import HTML  # or use ReportLab/xhtml2pdf as needed
from django.http import HttpResponse

def render_pdf(template_name, context_dict=None):
    """
    Render a Django template to PDF and return the PDF content as bytes.
    """
    # Render the HTML content using Django's template system
    html_content = render_to_string(template_name, context_dict or {})
    # Convert the HTML content to PDF. WeasyPrint's HTML.write_pdf() returns PDF bytes.
    pdf_content = HTML(string=html_content, base_url="").write_pdf()
    return pdf_content

def pdf_response(pdf_content, filename):
    """
    Wrap PDF bytes in an HTTP response with appropriate headers for download.
    """
    response = HttpResponse(pdf_content, content_type='application/pdf')
    # Set Content-Disposition to attachment (downloadable file) with a filename
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
