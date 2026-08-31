from recordfuse.normalize import normalize_email, normalize_name, normalize_phone

def test_name_removes_accents_and_punctuation():
    assert normalize_name(" José  da-Silva ") == "jose da silva"

def test_email_is_case_insensitive():
    assert normalize_email("JOSE@Example.COM") == "jose@example.com"

def test_phone_removes_formatting():
    assert normalize_phone("+61 (401) 234-567") == "61401234567"
