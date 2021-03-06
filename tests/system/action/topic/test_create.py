import simplejson as json

from tests.system.action.base import BaseActionTestCase


class TopicSystemTest(BaseActionTestCase):
    def test_create(self) -> None:
        self.create_model("topic/41", {})
        self.create_model("meeting/1", {"name": "test"})
        response = self.client.post(
            "/",
            json=[
                {
                    "action": "topic.create",
                    "data": [{"meeting_id": 1, "title": "test"}],
                }
            ],
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists("topic/42")
        topic = self.get_model("topic/42")
        self.assertEqual(topic.get("meeting_id"), 1)
        self.assertEqual(topic.get("agenda_item_id"), 1)
        self.assert_model_exists("agenda_item/1")
        agenda_item = self.get_model("agenda_item/1")
        self.assertEqual(agenda_item.get("meeting_id"), 1)
        self.assertEqual(agenda_item.get("content_object_id"), "topic/42")
        self.assert_model_exists(
            "list_of_speakers/1", {"content_object_id": "topic/42"}
        )
        self.assert_model_exists(
            "list_of_speakers/1", {"content_object_id": "topic/42"}
        )
        r = json.loads(response.data)
        self.assertTrue(r["success"])
        self.assertEqual(r["message"], "Actions handled successfully")
        self.assertEqual(r["results"], [[{"id": 42}]])

    def test_create_multi(self) -> None:
        self.create_model("meeting/1", {"name": "test"})
        response = self.client.post(
            "/",
            json=[
                {
                    "action": "topic.create",
                    "data": [
                        {"meeting_id": 1, "title": "test1"},
                        {"meeting_id": 1, "title": "test2"},
                    ],
                },
                {
                    "action": "topic.create",
                    "data": [
                        {"meeting_id": 1, "title": "test3"},
                        {"meeting_id": 1, "title": "test4"},
                    ],
                },
            ],
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists("topic/1")
        self.assert_model_exists("topic/2")
        self.assert_model_exists("topic/3")
        self.assert_model_exists("topic/4")
        r = json.loads(response.data)
        self.assertEqual(r["results"], [[{"id": 1}, {"id": 2}], [{"id": 3}, {"id": 4}]])

    def test_create_more_fields(self) -> None:
        self.create_model("meeting/1", {"name": "test"})
        response = self.client.post(
            "/",
            json=[
                {
                    "action": "topic.create",
                    "data": [
                        {
                            "meeting_id": 1,
                            "title": "test",
                            "agenda_type": 2,
                            "agenda_duration": 60,
                        }
                    ],
                }
            ],
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists("topic/1")
        topic = self.get_model("topic/1")
        self.assertEqual(topic.get("meeting_id"), 1)
        self.assertEqual(topic.get("agenda_item_id"), 1)
        self.assertTrue(topic.get("agenda_type") is None)
        agenda_item = self.get_model("agenda_item/1")
        self.assertEqual(agenda_item.get("meeting_id"), 1)
        self.assertEqual(agenda_item.get("content_object_id"), "topic/1")
        self.assertEqual(agenda_item["type"], 2)
        self.assertEqual(agenda_item["duration"], 60)
        self.assertEqual(agenda_item["weight"], 10000)

    def test_create_multiple(self) -> None:
        self.create_model("meeting/1", {})
        response = self.client.post(
            "/",
            json=[
                {
                    "action": "topic.create",
                    "data": [
                        {
                            "meeting_id": 1,
                            "title": "A",
                            "agenda_type": 1,
                            "agenda_weight": 1000,
                        },
                        {
                            "meeting_id": 1,
                            "title": "B",
                            "agenda_type": 1,
                            "agenda_weight": 1001,
                        },
                    ],
                }
            ],
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists("topic/1")
        topic = self.get_model("topic/1")
        self.assertEqual(topic.get("agenda_item_id"), 1)
        agenda_item = self.get_model("agenda_item/1")
        self.assertEqual(agenda_item.get("meeting_id"), 1)
        self.assertEqual(agenda_item.get("content_object_id"), "topic/1")
        self.assertEqual(agenda_item.get("type"), 1)
        self.assertEqual(agenda_item.get("weight"), 1000)
        topic = self.get_model("topic/2")
        self.assertEqual(topic.get("agenda_item_id"), 2)
        agenda_item = self.get_model("agenda_item/2")
        self.assertEqual(agenda_item.get("meeting_id"), 1)
        self.assertEqual(agenda_item.get("content_object_id"), "topic/2")
        self.assertEqual(agenda_item.get("type"), 1)
        self.assertEqual(agenda_item.get("weight"), 1001)
        meeting = self.get_model("meeting/1")
        self.assertEqual(meeting.get("topic_ids"), [1, 2])
        self.assertEqual(meeting.get("agenda_item_ids"), [1, 2])
        self.assertEqual(meeting.get("list_of_speakers_ids"), [1, 2])

    def test_create_multiple_with_multiple_actions(self) -> None:
        self.create_model("meeting/1", {})
        response = self.client.post(
            "/",
            json=[
                {
                    "action": "topic.create",
                    "data": [
                        {
                            "meeting_id": 1,
                            "title": "A",
                            "agenda_type": 1,
                            "agenda_weight": 1000,
                        },
                    ],
                },
                {
                    "action": "topic.create",
                    "data": [
                        {
                            "meeting_id": 1,
                            "title": "B",
                            "agenda_type": 1,
                            "agenda_weight": 1001,
                        },
                    ],
                },
            ],
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists("topic/1")
        topic = self.get_model("topic/1")
        self.assertEqual(topic.get("agenda_item_id"), 1)
        agenda_item = self.get_model("agenda_item/1")
        self.assertEqual(agenda_item.get("meeting_id"), 1)
        self.assertEqual(agenda_item.get("content_object_id"), "topic/1")
        self.assertEqual(agenda_item.get("type"), 1)
        self.assertEqual(agenda_item.get("weight"), 1000)
        topic = self.get_model("topic/2")
        self.assertEqual(topic.get("agenda_item_id"), 2)
        agenda_item = self.get_model("agenda_item/2")
        self.assertEqual(agenda_item.get("meeting_id"), 1)
        self.assertEqual(agenda_item.get("content_object_id"), "topic/2")
        self.assertEqual(agenda_item.get("type"), 1)
        self.assertEqual(agenda_item.get("weight"), 1001)
        meeting = self.get_model("meeting/1")
        self.assertEqual(meeting.get("topic_ids"), [1, 2])
        self.assertEqual(meeting.get("agenda_item_ids"), [1, 2])
        self.assertEqual(meeting.get("list_of_speakers_ids"), [1, 2])
