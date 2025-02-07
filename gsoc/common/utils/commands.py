import json
from smtplib import SMTPResponseException, SMTPSenderRefused

from django.core.mail import EmailMessage
from django.conf import settings

from django.template.loader import get_template
from django.template import TemplateDoesNotExist
from django.template import Template
from django.contrib.auth.models import User

from .irc import send_message

from gsoc.models import Scheduler, RegLink, GsocYear, UserProfile, Event


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
    try:
        send_email = EmailMessage(
            body=content,
            subject=settings.EMAIL_SUBJECT_PREFIX + data['subject'],
            from_email=settings.SERVER_EMAIL,
            reply_to=settings.REPLY_EMAIL,
            to=data['send_to'],
            )
        send_email.content_subtype = "html"
        send_email.send()
    except SMTPSenderRefused as e:
        last_error = json.dumps({
            "message": str(e),
            "smtp_code": e.smtp_code,
            })
        scheduler.last_error = last_error
        scheduler.success = False
        scheduler.save()
        return str(e)
    except SMTPResponseException as e:
        last_error = json.dumps({
            "message": str(e),
            "smtp_code": e.smtp_code,
            })
        scheduler.last_error = last_error
        scheduler.success = False
        scheduler.save()
        return str(e)
    except Exception as e:
        last_error = json.dumps({
            "message": str(e),
            })
        scheduler.last_error = last_error
        scheduler.success = False
        scheduler.save()
        return str(e)
    scheduler.last_error = None
    scheduler.success = True
    scheduler.save()
    return None


def deactivate_user(scheduler: Scheduler):
    """
    makes a user inactive when scheduled
    """
    try:
        u = User.objects.filter(pk=scheduler.data).first()
        u.is_active = False
        u.save()
        scheduler.success = True
        scheduler.save()
        return None
    except Exception as e:
        return str(e)


def send_irc_msgs(schedulers):
    """
    sends the irc messages from `send_irc_msg` `Scheduler` objects
    and returns any error encountered
    """
    try:
        send_message([_.data for _ in schedulers])
        for s in schedulers:
            s.success = True
            s.save()
        return None
    except Exception as e:
        return str(e)


def send_reg_reminder(scheduler: Scheduler):
    try:
        data = json.loads(scheduler.data)
        reglink = RegLink.objects.get(pk=data['object_pk'])
        if reglink.is_usable():
            return send_email(scheduler)
        else:
            return "link already used"
    except Exception as e:
        return str(e)


def add_blog_counter(scheduler: Scheduler):
    try:
        gsoc_year = GsocYear.objects.first()
        current_profiles = UserProfile.objects.filter(gsoc_year=gsoc_year, role=3).all()
        for profile in current_profiles:
            profile.current_blog_count += 1
            profile.save()
        return None
    except Exception as e:
        return str(e)


def add_calendar_event(scheduler: Scheduler):
    try:
        pk = json.loads(scheduler.data)['event']
        event = Event.objects.get(pk=pk)
        event.add_to_calendar()
        return None
    except Exception as e:
        return str(e)
