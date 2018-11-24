import jinja2

from dvhb_hybrid.mailer.template import EmailTemplate, FormatRender, TemplateRender

HTML = """
<html>
<head><title>title</title></head>
<body>
    <img src="../images/img.png" class>
    <IMG class SRC='/images/img.png'>
</body>
<html>
"""


def test_img():
    assert TemplateRender.re_img.search(HTML)


def test_email_template_from_html():
    template: jinja2.Template = FormatRender(HTML)
    e = EmailTemplate.create_from_jinja2(template)
    email_url = 'http://localhost/emails/'
    assert e.html.render(email_url=email_url) == HTML \
        .replace('src="../', 'src="' + email_url) \
        .replace("SRC='/", "SRC='" + email_url)
    assert e.subject.render() == 'title'
