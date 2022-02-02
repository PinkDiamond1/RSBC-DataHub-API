import pytest
import base64
import logging
import json
import responses
import python.prohibition_web_svc.middleware.keycloak_middleware as middleware
from datetime import datetime, timedelta
from python.prohibition_web_svc.models import Form, UserRole
from python.prohibition_web_svc.app import db, create_app
from python.prohibition_web_svc.config import Config


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def as_guest(app):
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def database(app):
    with app.app_context():
        db.init_app(app)
        db.create_all()
        yield db
        db.drop_all()
        db.session.commit()


@pytest.fixture
def forms(database):
    today = datetime.strptime("2021-07-21", "%Y-%m-%d")
    yesterday = today - timedelta(days=1)
    forms = [
        Form(form_id='AA-123332', form_type='24Hour', username='larry@idir', lease_expiry=today, printed=None),
        Form(form_id='AA-123333', form_type='24Hour', username='larry@idir', lease_expiry=yesterday, printed=None),
        Form(form_id='AA-123334', form_type='12Hour', username='larry@idir', lease_expiry=yesterday, printed=None),
        Form(form_id='AA-11111', form_type='24Hour', username=None, lease_expiry=None, printed=None)
    ]
    db.session.bulk_save_objects(forms)
    db.session.commit()


@pytest.fixture
def roles(database):
    today = datetime.strptime("2021-07-21", "%Y-%m-%d")
    user_role = [
        UserRole(username='john@idir', role_name='officer', submitted_dt=today),
        UserRole(username='larry@idir', role_name='officer', submitted_dt=today, approved_dt=today),
        UserRole(username='mo@idir', role_name='administrator', submitted_dt=today, approved_dt=today)
    ]
    db.session.bulk_save_objects(user_role)
    db.session.commit()


def test_authorized_user_gets_only_current_users_form_records(as_guest, monkeypatch, roles, forms):
    monkeypatch.setattr(middleware, "get_keycloak_certificates", _mock_keycloak_certificates)
    monkeypatch.setattr(middleware, "decode_keycloak_access_token", _get_authorized_user)
    resp = as_guest.get(Config.URL_PREFIX + "/api/v1/forms/24Hour",
                        content_type="application/json",
                        headers=_get_keycloak_auth_header(_get_keycloak_access_token()))
    assert len(resp.json) == 2
    assert resp.json == [
        {
             'id': 'AA-123332',
             'form_type': '24Hour',
             'lease_expiry': '2021-07-21',
             'printed_timestamp': None,
             'username': 'larry@idir'
         },
        {
            'id': 'AA-123333',
            'form_type': '24Hour',
            'lease_expiry': '2021-07-20',
            'printed_timestamp': None,
            'username': 'larry@idir'
        }
    ]
    assert resp.status_code == 200


def test_request_without_keycloak_user_cannot_get_forms(as_guest, monkeypatch, forms):
    monkeypatch.setattr(middleware, "get_keycloak_certificates", _mock_keycloak_certificates)
    resp = as_guest.get(Config.URL_PREFIX + "/api/v1/forms/24Hour",
                        content_type="application/json",
                        headers=_get_keycloak_auth_header("invalid"))
    assert resp.status_code == 401


def test_request_with_unauthorized_keycloak_user_cannot_get_forms(as_guest, monkeypatch, roles, forms):
    monkeypatch.setattr(middleware, "get_keycloak_certificates", _mock_keycloak_certificates)
    monkeypatch.setattr(middleware, "decode_keycloak_access_token", _get_unauthorized_user)
    resp = as_guest.get(Config.URL_PREFIX + "/api/v1/forms/24Hour",
                        content_type="application/json",
                        headers=_get_keycloak_auth_header(_get_keycloak_access_token()))
    assert resp.status_code == 401


def test_when_form_created_authorized_user_receives_unique_form_id_for_later_use(as_guest, monkeypatch, roles, forms):
    monkeypatch.setattr(middleware, "get_keycloak_certificates", _mock_keycloak_certificates)
    monkeypatch.setattr(middleware, "decode_keycloak_access_token", _get_authorized_user)
    resp = as_guest.post(Config.URL_PREFIX + "/api/v1/forms/24Hour",
                         content_type="application/json",
                         headers=_get_keycloak_auth_header(_get_keycloak_access_token()))
    today = datetime.now()
    expected_lease_expiry = datetime.strftime(today + timedelta(days=30), "%Y-%m-%d")

    assert resp.status_code == 201
    assert resp.json == {
        'id': 'AA-11111',
        'form_type': '24Hour',
        'lease_expiry': expected_lease_expiry,
        'printed_timestamp': None,
        'username': 'larry@idir'
    }


def test_unauthorized_user_cannot_create_new_forms(as_guest, monkeypatch, roles, forms):
    monkeypatch.setattr(middleware, "get_keycloak_certificates", _mock_keycloak_certificates)
    monkeypatch.setattr(middleware, "decode_keycloak_access_token", _get_unauthorized_user)
    resp = as_guest.post(Config.URL_PREFIX + "/api/v1/forms/24Hour",
                         content_type="application/json",
                         headers=_get_keycloak_auth_header(_get_keycloak_access_token()))
    today = datetime.now()
    expected_lease_expiry = datetime.strftime(today + timedelta(days=30), "%Y-%m-%d")
    assert resp.status_code == 401


def test_request_without_keycloak_user_cannot_create_forms(as_guest, monkeypatch, forms):
    monkeypatch.setattr(middleware, "get_keycloak_certificates", _mock_keycloak_certificates)
    resp = as_guest.post(Config.URL_PREFIX + "/api/v1/forms/24Hour",
                         content_type="application/json",
                         headers=_get_keycloak_auth_header("invalid"))
    assert resp.status_code == 401


def test_if_no_unique_ids_available_user_receives_a_500_response(as_guest, database, monkeypatch, roles):
    monkeypatch.setattr(middleware, "get_keycloak_certificates", _mock_keycloak_certificates)
    monkeypatch.setattr(middleware, "decode_keycloak_access_token", _get_authorized_user)
    today = datetime.strptime("2021-07-21", "%Y-%m-%d")
    forms = [
        Form(form_id='AA-123332', form_type='24Hour', username='other_user', lease_expiry=today, printed=None),
    ]
    database.session.bulk_save_objects(forms)
    database.session.commit()

    resp = as_guest.post(Config.URL_PREFIX + "/api/v1/forms/24Hour",
                         content_type="application/json",
                         headers=_get_keycloak_auth_header(_get_keycloak_access_token()))
    assert resp.status_code == 500


@responses.activate
def test_users_cannot_submit_payloads_to_the_create_endpoint(as_guest, monkeypatch, database, roles):
    monkeypatch.setattr(middleware, "get_keycloak_certificates", _mock_keycloak_certificates)
    monkeypatch.setattr(middleware, "decode_keycloak_access_token", _get_authorized_user)
    resp = as_guest.post(Config.URL_PREFIX + "/api/v1/forms/24Hour",
                         content_type="application/json",
                         data=json.dumps({"attribute": "value"}),
                         headers=_get_keycloak_auth_header(_get_keycloak_access_token()))
    assert resp.status_code == 400


def test_user_cannot_renew_lease_on_form_that_has_been_printed(as_guest, database, monkeypatch, roles):
    monkeypatch.setattr(middleware, "get_keycloak_certificates", _mock_keycloak_certificates)
    monkeypatch.setattr(middleware, "decode_keycloak_access_token", _get_authorized_user)
    today = datetime.strptime("2021-07-21", "%Y-%m-%d")
    forms = [
        Form(form_id='AA-123332', form_type='24Hour', username='larry@idir', lease_expiry=today, printed=today),
    ]
    database.session.bulk_save_objects(forms)
    database.session.commit()

    resp = as_guest.patch(Config.URL_PREFIX + "/api/v1/forms/24Hour/{}".format('AA-123332'),
                          content_type="application/json",
                          headers=_get_keycloak_auth_header(_get_keycloak_access_token()))
    assert resp.status_code == 400


def test_request_without_keycloak_user_cannot_update_forms_or_renew_lease_on_form(as_guest, monkeypatch, forms):
    monkeypatch.setattr(middleware, "get_keycloak_certificates", _mock_keycloak_certificates)
    resp = as_guest.patch(Config.URL_PREFIX + "/api/v1/forms/24Hour/{}".format("AA-123332"),
                          content_type="application/json",
                          headers=_get_keycloak_auth_header("invalid"))
    assert resp.status_code == 401


def test_when_form_updated_without_payload_user_receives_updated_lease_date(as_guest, monkeypatch, roles, forms):
    monkeypatch.setattr(middleware, "get_keycloak_certificates", _mock_keycloak_certificates)
    monkeypatch.setattr(middleware, "decode_keycloak_access_token", _get_authorized_user)
    resp = as_guest.patch(Config.URL_PREFIX + "/api/v1/forms/24Hour/{}".format('AA-123332'),
                          content_type="application/json",
                          headers=_get_keycloak_auth_header(_get_keycloak_access_token()))
    today = datetime.now()
    expected_lease_expiry = datetime.strftime(today + timedelta(days=30), "%Y-%m-%d")

    assert resp.status_code == 200
    assert resp.json == {
        'id': 'AA-123332',
        'form_type': '24Hour',
        'lease_expiry': expected_lease_expiry,
        'printed_timestamp': None,
        'username': 'larry@idir'
    }


def test_form_delete_method_not_implemented(as_guest):
    resp = as_guest.delete(Config.URL_PREFIX + "/api/v1/forms/24Hour/{}".format('AA-123332'),
                           content_type="application/json",
                           headers=_get_keycloak_auth_header(Config))
    assert resp.status_code == 405
    assert resp.json == {"error": "method not implemented"}


def _get_keycloak_access_token() -> str:
    return 'some-secret-access-token'


def _get_keycloak_auth_header(access_token) -> dict:
    return dict({
        'Authorization': 'Bearer {}'.format(access_token)
    })


def _mock_keycloak_certificates(**kwargs) -> tuple:
    logging.warning("inside _mock_keycloak_certificates()")
    return True, kwargs


def _get_unauthorized_user(**kwargs) -> tuple:
    logging.warning("inside _get_unauthorized_user()")
    kwargs['decoded_access_token'] = {'preferred_username': 'john@idir'}  # keycloak username
    return True, kwargs


def _get_authorized_user(**kwargs) -> tuple:
    logging.warning("inside _get_authorized_user()")
    kwargs['decoded_access_token'] = {'preferred_username': 'larry@idir'}  # keycloak username
    return True, kwargs


def _get_administrative_user_from_database(**kwargs) -> tuple:
    kwargs['decoded_access_token'] = {'preferred_username': 'mo@idir'}
    return True, kwargs