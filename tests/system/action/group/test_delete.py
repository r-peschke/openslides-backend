from tests.system.action.base import BaseActionTestCase


class GroupDeleteActionTest(BaseActionTestCase):
    def test_delete_correct(self) -> None:
        self.create_model("meeting/22", {"name": "name_meeting_22", "group_ids": [111]})
        self.create_model("group/111", {"name": "name_srtgb123", "meeting_id": 22})
        response = self.client.post(
            "/",
            json=[{"action": "group.delete", "data": [{"id": 111}]}],
        )

        self.assert_status_code(response, 200)
        self.assert_model_deleted("group/111")

    def test_delete_wrong_id(self) -> None:
        self.create_model("meeting/22", {"name": "name_meeting_22", "group_ids": [111]})
        self.create_model("group/112", {"name": "name_srtgb123", "meeting_id": 22})
        response = self.client.post(
            "/",
            json=[{"action": "group.delete", "data": [{"id": 111}]}],
        )
        self.assert_status_code(response, 400)
        model = self.get_model("group/112")
        assert model.get("name") == "name_srtgb123"

    def test_delete_default_group(self) -> None:
        self.create_model("meeting/22", {"name": "name_meeting_22", "group_ids": [111]})
        self.create_model(
            "group/111",
            {
                "name": "name_srtgb123",
                "default_group_for_meeting_id": 22,
                "meeting_id": 22,
            },
        )
        response = self.client.post(
            "/",
            json=[{"action": "group.delete", "data": [{"id": 111}]}],
        )

        self.assert_status_code(response, 400)

    def test_delete_superadmin_group(self) -> None:
        self.create_model("meeting/22", {"name": "name_meeting_22", "group_ids": [111]})
        self.create_model(
            "group/111",
            {
                "name": "name_srtgb123",
                "superadmin_group_for_meeting_id": 22,
                "meeting_id": 22,
            },
        )
        response = self.client.post(
            "/",
            json=[{"action": "group.delete", "data": [{"id": 111}]}],
        )

        self.assert_status_code(response, 400)
