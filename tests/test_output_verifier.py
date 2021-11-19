from jericho.plugin.output_verifier import OutputVerifier


def test_is_yaml():
    ov = OutputVerifier()
    bogus = """test:
  data: tep"""
    assert ov._is_yaml(bogus) == True


def test_verify_yaml():
    ov = OutputVerifier()
    bogus = """test:
  data: tep"""
    assert ov.verify(bogus, "YML") == True


def test_json_is_not_yml():
    ov = OutputVerifier()
    bogus = """{"test": "testing"}"""
    assert ov.verify(bogus, "YML") == False


def test_is_not_yaml():
    ov = OutputVerifier()
    bogus = """yeehaa!"""
    assert ov._is_yaml(bogus) == False


def test_verify_not_yaml():
    ov = OutputVerifier()
    bogus = """yeehaa!"""
    assert ov.verify(bogus, "YML") == False


def test_is_json():
    ov = OutputVerifier()
    bogus = """{"hej": "tjena"}"""
    assert ov._is_json(bogus) == True


def test_verify_json():
    ov = OutputVerifier()
    bogus = """{"hej": "tjena"}"""
    assert ov.verify(bogus, "JSON") == True


def test_is_not_json():
    ov = OutputVerifier()
    bogus = """stop hacking pls"""
    assert ov._is_json(bogus) == False


def test_is_not_json():
    ov = OutputVerifier()
    bogus = """stop hacking pls"""
    assert ov.verify(bogus, "JSON") == False


def test_is_xml():
    ov = OutputVerifier()
    bogus = """<?xml version="1.0" encoding="UTF-8"?>
<test>
    <aaa>hello</aaa>
</test>"""
    assert ov._is_xml(bogus) == True


def test_is_html_not_xml():
    ov = OutputVerifier()
    f = open("tests/assets/sample.html", "r")
    bogus = f.read()

    assert ov._is_xml(bogus) == False


def test_is_wordpress_manifest_is_xml():
    ov = OutputVerifier()
    f = open("tests/assets/wpmanifest.xml", "r")
    bogus = f.read()

    assert ov._is_xml(bogus) == True


def test_verify_xml():
    ov = OutputVerifier()
    bogus = """<?xml version="1.0" encoding="UTF-8"?>
<test>
    <aaa>hello</aaa>
</test>"""
    assert ov.verify(bogus, "XML") == True


def test_is_not_xml():
    ov = OutputVerifier()
    bogus = """stop hax"""
    assert ov._is_xml(bogus) == False


def test_verify_not_xml():
    ov = OutputVerifier()
    bogus = """stop hax"""
    assert ov.verify(bogus, "XML") == False


def test_is_xml_and_not_html():
    ov = OutputVerifier()
    bogus = """<html>hello</html>"""
    assert ov._is_xml(bogus) == False


def test_sso_html_is_not_xml():
    ov = OutputVerifier()
    bogus = """<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
    <head>
    </head>
    <body onload="document.forms[0].submit()">
        <noscript>
            <p>
                <strong>Note:</strong> Since your browser does not support JavaScript,
                you must press the Continue button once to proceed.
            </p>
        </noscript>
        
        <form action="https&#x3a;&#x2f;&#x2f;pf-ng.us.dell.com&#x2f;idp&#x2f;SSO.saml2" method="post">
            <div>
<input type="hidden" name="RelayState" value="https&#x3a;&#x2f;&#x2f;licensing.emc.com"/>                
<input type="hidden" name="SAMLRequest" value="PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPHNhbWwycDpBdXRoblJlcXVlc3QgQXNzZXJ0aW9uQ29uc3VtZXJTZXJ2aWNlVVJMPSJodHRwczovL2xpY2Vuc2luZy5lbWMuY29tL3NhbWwvU1NPIiBEZXN0aW5hdGlvbj0iaHR0cHM6Ly9wZi1uZy51cy5kZWxsLmNvbS9pZHAvU1NPLnNhbWwyIiBGb3JjZUF1dGhuPSJ0cnVlIiBJRD0iYTJkZDVjMzhlMmU0MzE2MzM0aWExYjhiY2c3ZzgyaiIgSXNQYXNzaXZlPSJmYWxzZSIgSXNzdWVJbnN0YW50PSIyMDIxLTEwLTAyVDE1OjQwOjI0LjM5OFoiIFByb3RvY29sQmluZGluZz0idXJuOm9hc2lzOm5hbWVzOnRjOlNBTUw6Mi4wOmJpbmRpbmdzOkhUVFAtUE9TVCIgVmVyc2lvbj0iMi4wIiB4bWxuczpzYW1sMnA9InVybjpvYXNpczpuYW1lczp0YzpTQU1MOjIuMDpwcm90b2NvbCI+PHNhbWwyOklzc3VlciB4bWxuczpzYW1sMj0idXJuOm9hc2lzOm5hbWVzOnRjOlNBTUw6Mi4wOmFzc2VydGlvbiI+aHR0cHM6Ly9saWNlbnNpbmcuZW1jLmNvbTwvc2FtbDI6SXNzdWVyPjxzYW1sMnA6U2NvcGluZyBQcm94eUNvdW50PSIyIi8+PC9zYW1sMnA6QXV0aG5SZXF1ZXN0Pg=="/>                
                
            </div>
            <noscript>
                <div>
                    <input type="submit" value="Continue"/>
                </div>
            </noscript>
        </form>
    </body>
</html>"""
    assert ov._is_xml(bogus) == False


def test_404_is_not_yml():
    bogus = """<!DOCTYPE html>
<html class='poplar'>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="X-UA-Compatible" content="ie=edge">
        <link rel="shortcut icon" href="https://d672eyudr6aq1.cloudfront.net/img/favicon_2015-07-29.ico">
        <title>Shared via Sprout Social</title>
        <meta name="description" content="Shared via Sprout Social">
        <meta name="robots" content="noindex, nofollow" />
        <style>
            html, body {
                margin: 0 !important;
                padding: 0 !important;
            }
        </style>
    </head>
    <body>
        <div id="PoplarExperienceShell"></div>
        <section id="PoplarAppContainer"></section>
        <footer id="PoplarExperienceFooter"></footer>
    <script type="text/javascript" src="/scripts/main.468a4c89.js"></script></body>
</html>"""
    ov = OutputVerifier()
    assert ov._is_yaml(bogus) == False


def test_404_is_no_spaces():
    bogus = """<!DOCTYPE html>
<html class='poplar'>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="X-UA-Compatible" content="ie=edge">
        <link rel="shortcut icon" href="https://d672eyudr6aq1.cloudfront.net/img/favicon_2015-07-29.ico">
        <title>Shared via Sprout Social</title>
        <meta name="description" content="Shared via Sprout Social">
        <meta name="robots" content="noindex, nofollow" />
        <style>
            html, body {
                margin: 0 !important;
                padding: 0 !important;
            }
        </style>
    </head>
    <body>
        <div id="PoplarExperienceShell"></div>
        <section id="PoplarAppContainer"></section>
        <footer id="PoplarExperienceFooter"></footer>
    <script type="text/javascript" src="/scripts/main.468a4c89.js"></script></body>
</html>"""
    ov = OutputVerifier()
    assert ov._is_no_spaces(bogus) == False


def test_404_is_no_spaces_gitignore():
    bogus = """# This is my gitignore
crap/
stuff
.secrets"""
    ov = OutputVerifier()
    assert ov._is_no_spaces(bogus) == True


def test_not_html_example_1():
    f = open("tests/assets/html_example_1.html", "r")
    bogus = f.read()
    ov = OutputVerifier()
    assert ov.verify(bogus, "NOT_HTML") == False


def test_xml_is_not_html():
    bogus = """<?xml version="1.0" encoding="UTF-8"?>
<note>
  <to>Tove</to>
  <from>Jani</from>
  <heading>Reminder</heading>
  <body>Don't forget me this weekend!</body>
</note>"""
    ov = OutputVerifier()
    assert ov.verify(bogus, "HTML") == False


def test_xml_is_not_yml():
    bogus = "<?xml version='1.0'><test>test</test>"

    ov = OutputVerifier()
    assert ov.verify(bogus, "YML") == False


def test_wordpress_license_is_text():
    f = open("tests/assets/wordpress_license.txt", "r")
    bogus = f.read()

    ov = OutputVerifier()
    assert ov.verify(bogus, "TEXT") == True


def test_no_spaces():
    ov = OutputVerifier()
    assert ov.verify("testing", "NO_SPACES") == True


def test_no_spaces_false():
    ov = OutputVerifier()
    assert ov.verify("test ing", "NO_SPACES") == False


def test_no_spaces_ignore_comments():
    ov = OutputVerifier()
    assert ov.verify("#test asd", "NO_SPACES") == True


def test_invalid_pattern():
    ov = OutputVerifier()
    assert ov.verify("testing blah asd", "blah") == False


def test_contain_html_tags_is_text():
    ov = OutputVerifier()
    assert ov.verify("<p>hello</p>", "TEXT") == False


def test_contain_non_html_tags_is_not_html():
    ov = OutputVerifier()
    assert ov.verify("<aaa>hello</aaa>", "TEXT") == True


def test_contain_is_text_not_xml_content():
    ov = OutputVerifier()
    assert ov._is_text("<?xml><asd>test</asd>") == False


def test_contain_is_text_not_yaml_content():
    ov = OutputVerifier()
    assert ov._is_text("testing: yep: sure: hmmm") == True


def test_contain_is_text_with_yaml_content():
    ov = OutputVerifier()
    assert ov._is_text("testing: yep") == False


def test_contain_is_text_with_json_content():
    ov = OutputVerifier()
    assert ov._is_text('{"test": "testing"}') == False
