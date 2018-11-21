import jinja2

from dvhb_hybrid.mailer.template import EmailTemplate, FormatRender

HTML = """
<html>
<head><title>title</title></head>
<body></body>
<html>
"""


def test_email_template_from_html():
    template: jinja2.Template = FormatRender(HTML)
    e = EmailTemplate.create_from_jinja2(template)
    assert e.html.render() == HTML
    assert e.subject.render() == 'title'
