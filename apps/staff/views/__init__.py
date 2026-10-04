from .auth import RememberMeLoginView, staff_only
from .dashboard import index, appointments_chart
from .appointments import appointments, appointments_form
from .patients import patients, download_patient_document
from .content import (
    blog_post_bulk_action,
    blog_post_create,
    blog_post_delete,
    blog_post_edit,
    blog_post_toggle_publish,
    blog_posts,
    testimonial_bulk_action,
    testimonial_create,
    testimonial_delete,
    testimonial_edit,
    testimonial_toggle_publish,
    testimonials,
    services,
    service_create,
    service_edit,
    service_delete,
    service_toggle_publish,
    team_members,
    team_member_create,
    team_member_edit,
    team_member_delete,
    team_member_toggle_publish,
)
from .pages import inquiries, message, profile, settings_page, website
