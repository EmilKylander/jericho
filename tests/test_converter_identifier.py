from jericho.converters.identifier import Identifier


async def test_check_successful_conversion():
    a = Identifier()

    assert a.run(
        "123.123.132.123",
        "https://google.com",
        200,
        "test: aaa",
        "<b>my content here</b><title>testing</title><a href='tel:+46234234'>aa</a><a href='mailto:test@test.com'>asd</a><a href='https://yahoo.com'>asd</a><script>ga('create', 'trackingcode', 'auto');</script><meta name='description' content='desc'><meta name='generator' content='ametys'>",
    ) == {
        "status": 200,
        "headers": "test: aaa",
        "domain": "https://google.com",
        "tech": [{'plugins': '', 'technology': 'Ametys', 'theme': '', 'version': ''}],
        "domains_found": ["https://yahoo.com"],
        "title": "testing",
        "description": "desc",
        "phones": ["+46234234"],
        "emails": ["test@test.com"],
        "ip": "123.123.132.123",
        "google_tracking_code": "trackingcode",
        "text_content": "my content here testingaaasdasd",
        "bytes": 281,
    }
