from typing import Any, Dict, List, Sequence, Union

import simplejson as json
from simplejson.errors import JSONDecodeError

from ...shared.exceptions import DatastoreException
from ...shared.filters import And, Filter, FilterOperator
from ...shared.interfaces.logging import LoggingModule
from ...shared.interfaces.write_request_element import WriteRequestElement
from ...shared.patterns import (
    Collection,
    CollectionField,
    FullQualifiedField,
    FullQualifiedId,
)
from . import commands
from .deleted_models_behaviour import DeletedModelsBehaviour
from .http_engine import HTTPEngine as Engine
from .interface import Aggregate, Count, DatastoreService, Found, PartialModel

# TODO: Use proper typing here.
DatastoreResponse = Any


class DatastoreAdapter(DatastoreService):
    """
    Adapter to connect to readable and writeable datastore.
    """

    # The key of this dictionary is a stringified FullQualifiedId or FullQualifiedField or CollectionField
    locked_fields: Dict[str, int]

    def __init__(self, engine: Engine, logging: LoggingModule) -> None:
        self.logger = logging.getLogger(__name__)
        self.engine = engine
        self.locked_fields = {}

    def retrieve(self, command: commands.Command) -> DatastoreResponse:
        """
        Uses engine to send data to datastore and retrieve result.

        This method also checks the payload and decodes JSON body.
        """
        content, status_code = self.engine.retrieve(command.name, command.data)
        if len(content):
            try:
                payload = json.loads(content)
            except JSONDecodeError:
                error_message = f"Bad response from datastore service. Body does not contain valid JSON. Received: {str(content)}"
                raise DatastoreException(error_message)
        else:
            payload = None
        self.logger.debug(f"Get response with status code {status_code}: {payload}")
        if status_code >= 400:
            error_message = f"Datastore service sends HTTP {status_code}."
            additional_error_message = (
                payload.get("error") if isinstance(payload, dict) else None
            )
            if additional_error_message is not None:
                if (
                    additional_error_message.get("type_verbose")
                    == "MODEL_DOES_NOT_EXIST"
                ):
                    error_message = " ".join(
                        (
                            error_message,
                            f"Model '{additional_error_message.get('fqid')}' does not exist.",
                        )
                    )
                else:
                    error_message = " ".join(
                        (error_message, str(additional_error_message))
                    )
            raise DatastoreException(error_message)
        return payload

    def get(
        self,
        fqid: FullQualifiedId,
        mapped_fields: List[str] = None,
        position: int = None,
        get_deleted_models: DeletedModelsBehaviour = None,
        lock_result: bool = False,
    ) -> PartialModel:
        mapped_fields_set = set()
        if mapped_fields:
            mapped_fields_set.update(mapped_fields)
            if lock_result:
                mapped_fields_set.add("meta_position")
        command = commands.Get(
            fqid=fqid,
            mapped_fields=mapped_fields_set,
            position=position,
            get_deleted_models=get_deleted_models,
        )
        self.logger.debug(
            f"Start GET request to datastore with the following data: {command.data}"
        )
        response = self.retrieve(command)
        if lock_result:
            instance_position = response.get("meta_position")
            if instance_position is None:
                raise DatastoreException(
                    "Response from datastore does not contain field 'meta_position' but this is required."
                )
            self.update_locked_fields(fqid, instance_position)
        return response

    def get_many(
        self,
        get_many_requests: List[commands.GetManyRequest],
        mapped_fields: List[str] = None,
        position: int = None,
        get_deleted_models: DeletedModelsBehaviour = None,
        lock_result: bool = False,
    ) -> Dict[Collection, Dict[int, PartialModel]]:
        if mapped_fields is not None:
            raise NotImplementedError(
                "The keyword 'mapped_fields' is not supported. Please use mapped_fields inside the GetManyRequest."
            )
        if lock_result:
            for get_many_request in get_many_requests:
                if get_many_request.mapped_fields is not None:
                    get_many_request.mapped_fields.add("meta_position")

        command = commands.GetMany(
            get_many_requests=get_many_requests,
            mapped_fields=mapped_fields,
            position=position,
            get_deleted_models=get_deleted_models,
        )
        self.logger.debug(
            f"Start GET_MANY request to datastore with the following data: {command.data}"
        )
        response = self.retrieve(command)
        result = {}
        for collection_str in response.keys():
            inner_result = {}
            collection = Collection(collection_str)
            for id_str, value in response[collection_str].items():
                instance_id = int(id_str)
                if lock_result:
                    instance_position = value.get("meta_position")
                    if instance_position is None:
                        raise DatastoreException(
                            "Response from datastore does not contain field 'meta_position' but this is required."
                        )
                    fqid = FullQualifiedId(collection, instance_id)
                    self.update_locked_fields(fqid, instance_position)
                inner_result[instance_id] = value
            result[collection] = inner_result
        return result

    def get_all(
        self,
        collection: Collection,
        mapped_fields: List[str] = None,
        get_deleted_models: DeletedModelsBehaviour = None,
        lock_result: bool = False,
    ) -> Dict[int, PartialModel]:
        mapped_fields_set = set()
        if mapped_fields:
            mapped_fields_set.update(mapped_fields)
            if lock_result:
                mapped_fields_set.update(("id", "meta_position"))
        command = commands.GetAll(
            collection=collection,
            mapped_fields=mapped_fields_set,
            get_deleted_models=get_deleted_models,
        )
        self.logger.debug(
            f"Start GET_ALL request to datastore with the following data: {command.data}"
        )
        response = self.retrieve(command)
        if lock_result:
            for item in response:
                instance_id = item.get("id")
                instance_position = item.get("meta_position")
                if instance_id is None or instance_position is None:
                    raise DatastoreException(
                        "Response from datastore does not contain fields 'id' and 'meta_position' but they are both required."
                    )
                fqid = FullQualifiedId(collection=collection, id=instance_id)
                self.update_locked_fields(fqid, instance_position)
        return response

    def filter(
        self,
        collection: Collection,
        filter: Filter,
        mapped_fields: List[str] = None,
        get_deleted_models: DeletedModelsBehaviour = None,
        lock_result: bool = False,
    ) -> Dict[int, PartialModel]:
        mapped_fields_set = set()
        if mapped_fields:
            mapped_fields_set.update(mapped_fields)
            if lock_result:
                mapped_fields_set.update(("id", "meta_position"))
        # by default, only filter for existing models
        if get_deleted_models != DeletedModelsBehaviour.ALL_MODELS:
            deleted_models_filter = FilterOperator(
                "meta_deleted",
                "=",
                get_deleted_models == DeletedModelsBehaviour.ONLY_DELETED,
            )
            filter = And(filter, deleted_models_filter)
        command = commands.Filter(
            collection=collection, filter=filter, mapped_fields=mapped_fields_set
        )
        self.logger.debug(
            f"Start FILTER request to datastore with the following data: {command.data}"
        )
        response = self.retrieve(command)
        if lock_result:
            for instance_id, item in response.items():
                instance_position = item.get("meta_position")
                if instance_id is None or instance_position is None:
                    raise DatastoreException(
                        "Response from datastore does not contain fields 'id' and 'meta_position' but they are both required."
                    )
                fqid = FullQualifiedId(collection=collection, id=instance_id)
                self.update_locked_fields(fqid, instance_position)
        response2 = dict()
        for key in response:
            response2[int(key)] = response[key]
        return response2

    def exists(
        self,
        collection: Collection,
        filter: Filter,
        lock_result: bool = False,
    ) -> Found:
        command = commands.Exists(collection=collection, filter=filter)
        self.logger.debug(
            f"Start EXISTS request to datastore with the following data: {command.data}"
        )
        response = self.retrieve(command)
        if lock_result:
            position = response.get("position")
            if position is None:
                raise DatastoreException("Invalid response from datastore.")
            raise NotImplementedError("Locking is not implemented")
        return {"exists": response["exists"]}

    def count(
        self,
        collection: Collection,
        filter: Filter,
        lock_result: bool = False,
    ) -> Count:
        command = commands.Count(collection=collection, filter=filter)
        self.logger.debug(
            f"Start COUNT request to datastore with the following data: {command.data}"
        )
        response = self.retrieve(command)
        if lock_result:
            raise NotImplementedError("Locking is not implemented")
        return {"count": response["count"]}

    def min(
        self, collection: Collection, filter: Filter, field: str, type: str = None
    ) -> Aggregate:
        # TODO: This method does not reflect the position of the fetched objects.
        command = commands.Min(
            collection=collection, filter=filter, field=field, type=type
        )
        self.logger.debug(
            f"Start MIN request to datastore with the following data: {command.data}"
        )
        response = self.retrieve(command)
        return response

    def max(
        self,
        collection: Collection,
        filter: Filter,
        field: str,
        type: str = None,
        lock_result: bool = False,
    ) -> Aggregate:
        """
        Per default records, marked as deleted, are counted
        """
        # TODO: This method does not reflect the position of the fetched objects.
        command = commands.Max(
            collection=collection, filter=filter, field=field, type=type
        )
        self.logger.debug(
            f"Start MAX request to datastore with the following data: {command.data}"
        )
        response = self.retrieve(command)
        if lock_result:
            self.update_locked_fields(
                CollectionField(collection, field), response.get("position")
            )
        return response

    def update_locked_fields(
        self,
        key: Union[FullQualifiedId, FullQualifiedField, CollectionField],
        position: int,
    ) -> None:
        """
        Updates the locked_fields map by adding the new value for the given FQId or
        FQField. To work properly in case of retry/reread we have to accept the new value always.
        """
        self.locked_fields[str(key)] = position

    def reserve_ids(self, collection: Collection, amount: int) -> Sequence[int]:
        command = commands.ReserveIds(collection=collection, amount=amount)
        self.logger.debug(
            f"Start RESERVE_IDS request to datastore with the following data: "
            f"Collection: {collection}, Amount: {amount}"
        )
        response = self.retrieve(command)
        return response.get("ids")

    def reserve_id(self, collection: Collection) -> int:
        return self.reserve_ids(collection=collection, amount=1)[0]

    def write(self, write_request_element: WriteRequestElement) -> None:
        command = commands.Write(
            write_request_element=write_request_element,
            locked_fields=self.locked_fields,
        )
        self.logger.debug(
            f"Start WRITE request to datastore with the following data: "
            f"Write request: {write_request_element}"
        )
        self.retrieve(command)

    def truncate_db(self) -> None:
        command = commands.TruncateDb()
        self.logger.debug("Start TRUNCATE_DB request to datastore")
        self.retrieve(command)
