from collections import defaultdict

from .decorators import method_connect_once


class ManyToManyRelationship:
    def __init__(self, app, model, target_model, source_field, target_field):
        self.app = app  # required for method_connect_once
        # Model for link (not source) table
        self.model = model
        self.target_model = target_model
        # Name of the FK to source model in the link model
        self.source_field = source_field
        # Name of the FK to target model in the link model
        self.target_field = target_field

    def _get_where_condition(self, field_name, field_id):
        col = self.model.table.c[field_name]
        if isinstance(field_id, (list, tuple, set)):
            where = col.in_(field_id)
        else:
            where = col == field_id
        return where

    def _get_source_where_condition(self, source):
        return self._get_where_condition(self.source_field, source)

    def _get_target_where_condition(self, target):
        return self._get_where_condition(self.target_field, target)

    @method_connect_once
    async def get_links_by_source(self, source, *, connection=None):
        """
        Returns links given source model ID/IDs
        :param source: Single or list of source model ID/IDs
        :param connection: DB connection to perform operation with
        """
        where = self._get_source_where_condition(source)
        return await self.model.get_list(where, connection=connection)

    @method_connect_once
    async def get_links_by_target(self, target, *, connection=None):
        """
        Returns links given target model ID/IDs
        :param target: Single or list of target model ID/IDs
        :param connection: DB connection to perform operation with
        """
        where = self._get_target_where_condition(target)
        return await self.model.get_list(where, connection=connection)

    @method_connect_once
    async def _get_targets(self, links, *, as_dict=False, connection=None):
        target_ids = [i[self.target_field] for i in links]
        pk_name = self.target_model.primary_key
        pk = self.target_model.table.c[pk_name]
        targets = await self.target_model.get_list(pk.in_(target_ids), connection=connection)
        if as_dict:
            targets = {i[pk_name]: i for i in targets}
        return targets

    @method_connect_once
    async def get_for_one(self, source, *, connection=None):
        links = await self.get_links_by_source(source, connection=connection)
        return await self._get_targets(links, connection=connection)

    @method_connect_once
    async def get_for_list(self, source, *, connection=None):
        links = await self.get_links_by_source(source, connection=connection)
        targets = await self._get_targets(links, as_dict=True, connection=connection)
        result = defaultdict(list)
        for i in links:
            source_key = i[self.source_field]
            target_key = i[self.target_field]
            result[source_key].append(targets[target_key])
        return dict(result)

    async def delete(self, source, *, connection=None):
        """
        For backward compatibility
        """

        await self.delete_by_source(source, connection=connection)

    @method_connect_once
    async def delete_by_source(self, source, *, connection=None):
        """
        Deletes links given source model ID/IDs
        :param source: Single or list of source model ID/IDs
        :param connection: DB connection to perform operation with
        """

        where = self._get_source_where_condition(source)
        await self.model.delete_where(where, connection=connection)

    @method_connect_once
    async def delete_by_target(self, target, *, connection=None):
        """
        Deletes links given target model ID/IDs
        :param target: Single or list of target model ID/IDs
        :param connection: DB connection to perform operation with
        """

        where = self._get_target_where_condition(target)
        await self.model.delete_where(where, connection=connection)
