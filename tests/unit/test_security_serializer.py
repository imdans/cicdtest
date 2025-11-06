from app.utils.security import make_serializer


def test_security_serializer_roundtrip(app):
    with app.app_context():
        s = make_serializer()
        token = s.dumps({"x": 1})
        data = s.loads(token)
        assert data == {"x": 1}
