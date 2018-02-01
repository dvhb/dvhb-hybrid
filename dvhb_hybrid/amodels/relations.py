from collections import defaultdict

from .decorators import method_connect_once


class ManyToManyRelationship:
    def __init__(self, app, model, target_model, source_field, target_field):
        self.app = app  # required for method_connect_once
        self.model = model
        self.target_model = target_model
        self.source_field = source_field
        self.target_field = target_field

    def _get_source_where_condition(self, source):
        col = self.model.table.c[self.source_field]
        if isinstance(source, (list, tuple, set)):
            where = col.in_(source)
        else:
            where = col == source
        return where

    @method_connect_once
    async def _get_source_links(self, source, *, connection=None):
        where = self._get_source_where_condition(source)
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
        links = await self._get_source_links(source, connection=connection)
        return await self._get_targets(links, connection=connection)

    @method_connect_once
    async def get_for_list(self, source, *, connection=None):
        links = await self._get_source_links(source, connection=connection)
        targets = await self._get_targets(links, as_dict=True, connection=connection)
        result = defaultdict(list)
        for i in links:
            source_key = i[self.source_field]
            target_key = i[self.target_field]
            result[source_key].append(targets[target_key])
        return dict(result)

    @method_connect_once
    async def delete(self, source, *, connection=None):
        where = self._get_source_where_condition(source)
        await self.model.delete_where(where, connection=connection)
