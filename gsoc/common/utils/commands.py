from smtplib import SMTPResponseException, SMTPSenderRefused
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import get_template
from django.template import TemplateDoesNotExist
from django.template import Template, Context
from gsoc.models import Scheduler
import json
from collections.abc import Sequence
from django.contrib.auth.models import User
from .irc import send_message


def build_send_mail_json(send_to,
                         template: str,
                         subject: str,
                         template_data: dict = None):
    if not isinstance(send_to, Sequence) and not isinstance(send_to, str):
        raise TypeError('send_to must be a sequence of email addresses '
                        'or one email address as str!')
    return json.dumps(locals())


def send_email(scheduler: Scheduler):
    data = json.loads(scheduler.data)
    try:
        data['template'] = get_template(f'email/{data["template"]}')
    except TemplateDoesNotExist:
        data['template'] = Template(data['template'])
    context_dict = {} if not data['template_data'] else data['template_data']
    content = data['template'].render(context_dict)
    if isinstance(data['send_to'], str):
        data['send_to'] = [data['send_to']]
    recipients_count = len(data['send_to'])
    try:
        sent_count = send_mail(
            message=content,
            subject=settings.EMAIL_SUBJECT_PREFIX + data['subject'],
            from_email=settings.SERVER_EMAIL,
            recipient_list=data['send_to'],
            fail_silently=False,
            html_message=content,
        )
    except SMTPSenderRefused as e:
        last_error = json.dumps({
            "message": str(e),
            "smtp_code": e.smtp_code,
        })
        scheduler.last_error = last_error
        scheduler.success = False
        scheduler.save()
        return None
    except SMTPResponseException as e:
        last_error = json.dumps({
            "message": str(e),
            "smtp_code": e.smtp_code,
        })
        scheduler.last_error = last_error
        scheduler.success = False
        scheduler.save()
        return None
    except Exception as e:
        last_error = json.dumps({
            "message": str(e),
        })
        scheduler.last_error = last_error
        scheduler.success = False
        scheduler.save()
        return None
    if sent_count < recipients_count:
        failed_count = recipients_count-sent_count
        scheduler.success = False
        last_error = json.dumps({
            "message": str(failed_count) + "emails aren't sent successfully",
        })
        scheduler.last_error = last_error
        scheduler.save()
    else:
        scheduler.last_error = None
        scheduler.success = True
        scheduler.save()
    return None


def deactivate_user(scheduler: Scheduler):
    """
    makes a user inactive when scheduled
    """
    u = User.objects.filter(pk=scheduler.data).first()
    u.is_active = False
    u.save()
    scheduler.success = True
    scheduler.save()
    return None

def send_irc_msgs(schedulers):
    """
    sends the irc messages from `send_irc_msg` `Scheduler` objects
    and returns any error encountered
    """
    send_message([_.data for _ in schedulers])
    for s in schedulers:
        s.success = True
        s.save()
    return None
