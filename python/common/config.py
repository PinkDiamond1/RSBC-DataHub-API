import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    LOG_FORMAT                          = "%(asctime)s::%(levelname)s::%(name)s::%(message)s"
    LOG_LEVEL                           = os.environ.get('LOG_LEVEL', 'WARNING').upper()

    RABBITMQ_URL                        = os.getenv('RABBITMQ_URL', 'localhost')
    RABBITMQ_USER                       = os.getenv('RABBITMQ_USER')
    RABBITMQ_PASS                       = os.getenv('RABBITMQ_PASS')
    RABBITMQ_PORT                       = os.getenv('RABBITMQ_PORT', '5672')
    RABBITMQ_EXCHANGE                   = os.getenv('RABBITMQ_EXCHANGE', '')
    MAX_CONNECTION_RETRIES              = os.getenv('MAX_CONNECTION_RETRIES', 25)
    RETRY_DELAY                         = os.getenv('RETRY_DELAY', 30)
    RABBITMQ_MESSAGE_ENCODE             = os.getenv('RABBITMQ_MESSAGE_ENCODE', 'utf-8')
    ENCRYPT_KEY                         = os.getenv('ENCRYPT_KEY')

    # Common Hosted Email Services API
    COMM_SERV_AUTH_URL                  = os.getenv('COMM_SERV_AUTH_URL', 'http://localhost')
    COMM_SERV_API_ROOT_URL              = os.getenv('COMM_SERV_API_ROOT_URL', 'http://localhost')
    COMM_SERV_REALM                     = os.getenv('COMM_SERV_REALM', 'realm')
    COMM_SERV_CLIENT_ID                 = os.getenv('COMM_SERV_CLIENT_ID', '')
    COMM_SERV_CLIENT_SECRET             = os.getenv('COMM_SERV_CLIENT_SECRET', '')

    ADMIN_EMAIL_ADDRESS                 = os.getenv('ADMIN_EMAIL_ADDRESS')
    REPLY_EMAIL_ADDRESS                 = os.getenv('REPLY_EMAIL_ADDRESS', 'do-not-reply-rsi@gov.bc.ca')

    # comma separated list of email addresses to receive a bcc of all outgoing emails
    BCC_EMAIL_ADDRESSES                 = os.getenv('BCC_EMAIL_ADDRESSES', 'fake1@gov.bc.ca, fake2@gov.bc.ca')

    # OpenShift Environment (dev, test, prod)
    ENVIRONMENT                         = os.getenv('ENVIRONMENT', 'dev')

    # Payload version number
    # This number is used in the validation schema to determine which payload version are accepted
    PAYLOAD_VERSION_NUMBER              = "1.5"

    # Splunk settings
    OPENSHIFT_PLATE                     = os.getenv('OPENSHIFT_PLATE', "be78d6")
    SPLUNK_HOST                         = os.getenv('SPLUNK_HOST', 'http://localhost')
    SPLUNK_PORT                         = int(os.getenv('SPLUNK_PORT', '8088'))
    SPLUNK_TOKEN                        = os.getenv('SPLUNK_TOKEN', 'aaaa-bbbb-cccc')
    LOGGERS_IN_USE                      = os.getenv('LOGGERS_IN_USE', 'console').split()

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(filename)s %(funcName)s %(levelname)s %(lineno)d %(module)s %(message)s %(pathname)s'
            },
            'brief': {
                'format': LOG_FORMAT
            }
        },
        'handlers': {
            'console': {
                'level': LOG_LEVEL,
                'class': 'logging.StreamHandler',
                'formatter': 'brief'
            }
        },
        'loggers': {
            '': {
                'handlers': LOGGERS_IN_USE,
                'level': LOG_LEVEL
            }
        }
    }

