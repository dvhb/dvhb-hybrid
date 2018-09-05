from dvhb_hybrid.amodels import method_connect_once


class MPTTMixin:
    """
    Add methods to work with models based on django MPTT model (https://github.com/django-mptt/django-mptt)

    See also: https://www.sitepoint.com/hierarchical-data-database/
    """

    parent_key = 'parent_id'  # TODO: take it from django model
    order_insertion_by = []   # TODO: take it from django model
    mptt_fields = ['id', parent_key, 'level', 'lft', 'rght', 'tree_id']

    @classmethod
    def _field_name(cls, name):
        if name == 'parent_id':
            return cls.parent_key
        elif name == 'id':
            return cls.primary_key
        return name

    def _field(self, name):
        return getattr(self, self._field_name(name))

    @classmethod
    def _column(cls, name):
        return getattr(cls.table.c, cls._field_name(name))

    def _tree_id_condition(self):
        return self._column('tree_id') == self.tree_id

    @method_connect_once
    async def get_ancestors(self, *, include_self=False, connection=None, **kwargs):
        where_args = [
            self._tree_id_condition(),
            self.table.c.lft <= self.lft if include_self else self.table.c.lft < self.lft,
            self.table.c.rght >= self.rght if include_self else self.table.c.rght > self.rght,
        ]
        return await super().get_list(*where_args, connection=connection, **kwargs)

    @method_connect_once
    async def get_children(self, *, connection=None, **kwargs):
        if self.is_leaf_node():
            return []
        where_args = [
            self._tree_id_condition(),
            self._column('parent_id') == self.pk
        ]
        return await super().get_list(*where_args, connection=connection, **kwargs)

    @method_connect_once
    async def get_descendants(self, include_self=False, *, connection=None, **kwargs):
        where_args = [
            self._tree_id_condition(),
            self.table.c.lft >= self.lft if include_self else self.table.c.lft > self.lft,
            self.table.c.rght <= self.rght if include_self else self.table.c.rght < self.rght,
        ]
        return await super().get_list(*where_args, connection=connection, **kwargs)

    def get_descendant_count(self):
        return (self.rght - self.lft) // 2

    @method_connect_once
    async def get_family(self, *, connection=None):
        ancestors = await self.get_ancestors(include_self=False, connection=connection)
        descendants = await self.get_descendants(include_self=True, connection=connection)
        return ancestors + descendants

    @method_connect_once
    async def get_next_sibling(self, *, connection=None, **kwargs):
        where_args = [
            self._tree_id_condition(),
            self.table.c.lft == self.rght + 1
        ]
        kwargs.setdefault('silent', True)
        return await super().get_one(*where_args, connection=connection, **kwargs)

    @method_connect_once
    async def get_previous_sibling(self, *, connection=None, **kwargs):
        if self.lft == 1:
            return
        where_args = [
            self._tree_id_condition(),
            self.table.c.rght == self.lft - 1
        ]
        kwargs.setdefault('silent', True)
        return await super().get_one(*where_args, connection=connection, **kwargs)

    @method_connect_once
    async def get_root(self, *, connection=None):
        if self.is_root_node():
            return self
        where_args = [
            self._tree_id_condition(),
            self._column('parent_id').is_(None),
            self.table.c.lft < self.lft,
            self.table.c.rght > self.rght,
        ]
        return await super().get_one(*where_args, connection=connection, silent=True)

    @method_connect_once
    async def get_siblings(self, *, include_self=False, connection=None, **kwargs):
        where_args = [
            self._tree_id_condition(),
            self._column('parent_id') == self._field('parent_id')
        ]
        if not include_self:
            where_args.append(self._column('id') != self.pk)
        return await super().get_list(*where_args, connection=connection, **kwargs)

    def is_child_node(self):
        return not self.is_root_node()

    def is_leaf_node(self):
        return (self.rght - self.lft) == 1

    def is_root_node(self):
        return self._field('parent_id') is None

    async def insert_at(self, target, position='first-child'):
        raise NotImplementedError

    async def move_to(target, position='first-child'):
        raise NotImplementedError

    @classmethod
    async def _get_tree_root_id(cls, tree_id, connection):
        where = [
            cls._column('parent_id').is_(None),
            cls._column('tree_id') == tree_id
        ]
        data = await super().get_one(*where, fields=[cls.primary_key], connection=connection)
        return data[cls.primary_key]

    @classmethod
    async def _fetch_child_ids(cls, parent_id, connection):
        parent_condition = (cls._column('parent_id') == parent_id)
        sort = None
        fields = [cls.primary_key]
        if cls.order_insertion_by:
            sort = list(map(cls._column, cls.order_insertion_by))
        data = await super().get_list(parent_condition, fields=fields, sort=sort, connection=connection)
        return map(lambda r: r[cls.primary_key], data)

    @classmethod
    async def _update_node(cls, node_id, left, right, connection):
        where = cls._column('id') == node_id
        await cls.update_fields(where, lft=left, rght=right, connection=connection)

    @classmethod
    async def _rebuild_subtree(cls, root_id, *, left=1, connection=None):
        right = left + 1  # in the case it is a leaf node
        child_ids = await cls._fetch_child_ids(root_id, connection)
        for child_id in child_ids:
            right = await cls._rebuild_subtree(root_id=child_id, left=right, connection=connection)
        await cls._update_node(root_id, left=left, right=right, connection=connection)
        return right + 1

    @classmethod
    @method_connect_once
    async def rebuild(cls, *, connection=None):
        """
        Rebuils MPTT indexes for all data (i.e. all subtrees)
        """
        top_ids = await cls._fetch_child_ids(None, connection)
        for top_id in top_ids:
            await cls._rebuild_subtree(top_id, connection=connection)

    @classmethod
    async def _get_rightmost_sibling(cls, parent_id, connection):
        where_args = [
            cls._column('parent_id') == parent_id,
        ]
        roots = await super().get_list(
            *where_args, fields=cls.mptt_fields, sort=[cls.table.c.rght.desc()], connection=connection)
        try:
            return roots[0]
        except IndexError:
            return

    @classmethod
    @method_connect_once
    async def create(cls, *, connection=None, rebuild=True, **kwargs):
        cls.set_defaults(kwargs)
        parent = None
        parent_id = kwargs.get(cls._field_name('parent_id'))
        if parent_id:
            parent = await cls.get_one(parent_id, fields=cls.mptt_fields, connection=connection)
        rightmost_sibling = await cls._get_rightmost_sibling(parent_id, connection)

        kwargs['level'] = 0 if not parent else parent['level'] + 1
        kwargs[cls._field_name('parent_id')] = parent.pk if parent else None
        kwargs['tree_id'] = \
            parent['tree_id'] if parent else rightmost_sibling['tree_id'] + 1 if rightmost_sibling else 1
        kwargs['lft'] = rightmost_sibling['rght'] + 1 if rightmost_sibling and parent_id else \
            parent['lft'] + 1 if parent else 1
        kwargs['rght'] = kwargs['lft'] + 1
        tree_node = await super().create(connection=connection, **kwargs)
        if rebuild and parent_id:
            # Regenerate MPTT indexes for the current subtree
            root_id = await cls._get_tree_root_id(kwargs['tree_id'], connection=connection)
            await cls._rebuild_subtree(root_id, connection=connection)
            # Refetch node created
            tree_node = await cls.get_one(tree_node.pk, connection=connection)
        return tree_node
