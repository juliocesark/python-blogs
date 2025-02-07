from .models import UserDetails, UserProfile, RegLink, BlogPostDueDate, Event

from django.forms import ModelForm, Select


class UserProfileForm(ModelForm):
    class Meta:
        model = UserProfile
        fields = (
            'role',
            'suborg_full_name',
            'gsoc_year',
            'accepted_proposal_pdf',
            'app_config',
            'hidden'
            )
        widgets = {
            'app_config': Select(),
            }


class ProposalUploadForm(ModelForm):
    class Meta:
        model = UserProfile
        fields = ['accepted_proposal_pdf']


class UserDetailsForm(ModelForm):
    class Meta:
        model = UserDetails
        fields = ('deactivation_date',)


class RegLinkForm(ModelForm):
    class Meta:
        model = RegLink
        fields = ('email', 'user_role', 'user_suborg', 'user_gsoc_year')


class BlogPostDueDateForm(ModelForm):
    class Meta:
        model = BlogPostDueDate
        fields = ('title', 'date')


class EventForm(ModelForm):
    class Meta:
        model = Event
        fields = ('title', 'start_date', 'end_date')
