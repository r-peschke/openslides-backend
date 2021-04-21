from typing import Any, Dict

from ....models.models import Meeting
from ....shared.patterns import Collection, FullQualifiedId
from ...generics.update import UpdateAction
from ...util.assert_belongs_to_meeting import assert_belongs_to_meeting
from ...util.default_schema import DefaultSchema
from ...util.register import register_action
from ..meeting.shared_meeting import used_as_default_for_schema_required

meeting_settings_keys = [
    "welcome_title",
    "welcome_text",
    "name",
    "description",
    "location",
    "start_time",
    "end_time",
    "url_name",
    "enable_anonymous",
    "conference_show",
    "conference_auto_connect",
    "conference_los_restriction",
    "conference_stream_url",
    "conference_stream_poster_url",
    "projector_countdown_default_time",
    "projector_countdown_warning_time",
    "export_csv_encoding",
    "export_csv_separator",
    "export_pdf_pagenumber_alignment",
    "export_pdf_fontsize",
    "export_pdf_pagesize",
    "agenda_show_subtitles",
    "agenda_enable_numbering",
    "agenda_number_prefix",
    "agenda_numeral_system",
    "agenda_item_creation",
    "agenda_new_items_default_visibility",
    "agenda_show_internal_items_on_projector",
    "list_of_speakers_amount_last_on_projector",
    "list_of_speakers_amount_next_on_projector",
    "list_of_speakers_couple_countdown",
    "list_of_speakers_show_amount_of_speakers_on_slide",
    "list_of_speakers_present_users_only",
    "list_of_speakers_show_first_contribution",
    "motions_default_workflow_id",
    "motions_default_amendment_workflow_id",
    "motions_default_statute_amendment_workflow_id",
    "motions_preamble",
    "motions_default_line_numbering",
    "motions_line_length",
    "motions_reason_required",
    "motions_enable_text_on_projector",
    "motions_enable_reason_on_projector",
    "motions_enable_sidebox_on_projector",
    "motions_enable_recommendation_on_projector",
    "motions_show_referring_motions",
    "motions_show_sequential_number",
    "motions_recommendations_by",
    "motions_statute_recommendations_by",
    "motions_recommendation_text_mode",
    "motions_default_sorting",
    "motions_number_type",
    "motions_number_min_digits",
    "motions_number_with_blank",
    "motions_statutes_enabled",
    "motions_amendments_enabled",
    "motions_amendments_in_main_list",
    "motions_amendments_of_amendments",
    "motions_amendments_prefix",
    "motions_amendments_text_mode",
    "motions_amendments_multiple_paragraphs",
    "motions_supporters_min_amount",
    "motions_export_title",
    "motions_export_preamble",
    "motions_export_submitter_recommendation",
    "motions_export_follow_recommendation",
    "motion_poll_ballot_paper_selection",
    "motion_poll_ballot_paper_number",
    "motion_poll_default_type",
    "motion_poll_default_100_percent_base",
    "motion_poll_default_majority_method",
    "motion_poll_default_group_ids",
    "users_sort_by",
    "users_enable_presence_view",
    "users_enable_vote_weight",
    "users_allow_self_set_present",
    "users_pdf_welcometitle",
    "users_pdf_welcometext",
    "users_pdf_url",
    "users_pdf_wlan_ssid",
    "users_pdf_wlan_password",
    "users_pdf_wlan_encryption",
    "users_email_sender",
    "users_email_replyto",
    "users_email_subject",
    "users_email_body",
    "assignments_export_title",
    "assignments_export_preamble",
    "assignment_poll_ballot_paper_selection",
    "assignment_poll_ballot_paper_number",
    "assignment_poll_add_candidates_to_list_of_speakers",
    "assignment_poll_sort_poll_result_by_votes",
    "assignment_poll_default_type",
    "assignment_poll_default_method",
    "assignment_poll_default_100_percent_base",
    "assignment_poll_default_majority_method",
    "assignment_poll_default_group_ids",
]


@register_action("meeting.update")
class MeetingUpdate(UpdateAction):
    model = Meeting()
    schema = DefaultSchema(Meeting()).get_update_schema(
        optional_properties=[
            *meeting_settings_keys,
            "template_for_committee_id",
            "guest_ids",
            "reference_projector_id",
        ],
        additional_optional_fields={
            "default_projector_$_id": used_as_default_for_schema_required,
        },
    )

    def update_instance(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        meeting_check = []
        if "reference_projector_id" in instance:
            if (
                reference_projector_id := instance["reference_projector_id"]
            ) and reference_projector_id:
                meeting_check.append(
                    FullQualifiedId(Collection("projector"), reference_projector_id)
                )
        if "default_projector_$_id" in instance:
            meeting_check.extend(
                [
                    FullQualifiedId(Collection("projector"), projector_id)
                    for projector_id in instance["default_projector_$_id"].values()
                    if projector_id
                ]
            )

        if meeting_check:
            assert_belongs_to_meeting(self.datastore, meeting_check, instance["id"])
        return instance