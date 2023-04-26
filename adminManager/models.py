from django.db import models
from django.db.models.functions import Upper

from django.forms.models import model_to_dict

#from djangowkb.fields import GeometryField
from .fields import GeometryField
from .geometry import WKBGeometry

import traceback

# Create your models here.

class Admin(models.Model):
    parent = models.ForeignKey('Admin', related_name='children', on_delete=models.CASCADE, 
                                blank=True, null=True)
    source = models.ForeignKey('AdminSource', related_name='admins', on_delete=models.CASCADE, 
                                blank=True, null=True)
    names = models.ManyToManyField('AdminName', related_name='admins')
    level = models.IntegerField(null=True, blank=True) # just to indicate the self-described admin-level of the ref
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    geom = GeometryField(null=True, blank=True)

    minx = models.FloatField(null=True, blank=True)
    miny = models.FloatField(null=True, blank=True)
    maxx = models.FloatField(null=True, blank=True)
    maxy = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['parent']), 
            models.Index(fields=['source']), 
            models.Index(fields=['minx']), 
            models.Index(fields=['miny']), 
            models.Index(fields=['maxx']), 
            models.Index(fields=['maxy']), 
        ]

    #def __str__(self):
    #    hierarchy_names = [p.names.first().name for p in self.get_all_parents()]
    #    return f'{", ".join(hierarchy_names)}'

    def save(self, *args, **kwargs):
        # auto set bbox attrs
        if self.geom: 
            if not isinstance(self.geom, WKBGeometry):
                self.geom = WKBGeometry(self.geom)
            self.minx,self.miny,self.maxx,self.maxy = self.geom.bbox()
        # normal save
        super(Admin, self).save(*args, **kwargs)

    @property
    def lineres(self):
        # not very efficient
        from core.utils import calc_stats
        geom = self.geom.__geo_interface__
        feat = {'type':'Feature', 'geometry':geom}
        stats = calc_stats(feats=[feat])
        return stats['statsLineResolution']

    def get_all_parents(self, include_self=True):
        '''Returns a list of all parents, starting with and including self.'''
        refs = [self]
        cur = self
        while cur.parent:
            cur = cur.parent
            refs.append(cur)
        return refs

    def get_all_children(self):
        '''Returns a list of all children.'''
        results = []
        for child in self.children.all():
            subchildren = child.get_all_children()
            results.append( {'item':child, 'children':subchildren} )
        return results

    def full_name(self):
        all_refs = self.get_all_parents()
        full_name = ', '.join([ref.names.first().name for ref in all_refs])
        return full_name

    def serialize(self, geom=True):
        hierarchy = [{'id':p.id, 
                        'names':[n.name for n in p.names.all()], 
                        'level':p.level,
                        }
                        for p in self.get_all_parents()]
        source = self.source
        source_name = ' - '.join((s.name for s in source.get_all_parents_reversed()))
        dct = {'id':self.pk,
                'hierarchy':hierarchy,
                'source':{'name':source_name, 'id':source.pk},
                'valid_from':self.valid_from,
                'valid_to':self.valid_to,
                'lineres':self.lineres,
                }
        if geom:
            dct['geom'] = self.geom.__geo_interface__
        return dct

class AdminName(models.Model):
    name = models.CharField(max_length=100)

    # for now just manually add index w collate nocase
    class Meta:
        indexes = [
            models.Index(Upper('name'),
                        name='admin_name_upper_idx'), 
        ]

    def __str__(self):
        return f'{self.name}'

class AdminSource(models.Model):
    SOURCE_TYPES = [
        ('DataSource', 'Data Source'),
        ('MapSource', 'Map Source'),
    ]
    type = models.CharField(max_length=50,
                            choices=SOURCE_TYPES)
    parent = models.ForeignKey('AdminSource', related_name='children', on_delete=models.CASCADE, 
                                blank=True, null=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    sources = models.ManyToManyField("AdminSource", blank=True, null=True)

    def children_with_stats(self):
        '''Immediate children with stats as a list of (child,stats) tuples'''
        # NOTE: this is very messy and probably not the best approach

        # get immediate children
        from django.db import connection
        curs = connection.cursor()
        children = self.children.all()
        child_ids = [c.pk for c in children]
        if not child_ids:
            return []

        # custom aggregation with group by
        curs.execute('''
            WITH RECURSIVE recurs AS
            (
                SELECT id, id AS root_id FROM {sources_table} WHERE id IN {child_ids}

                UNION ALL

                SELECT s.id, recurs.root_id FROM recurs
                INNER JOIN {sources_table} AS s
                ON s.parent_id = recurs.id
            )
            SELECT root_id AS id, COUNT(admins.id) AS admin_count
            FROM recurs
            INNER JOIN {admin_table} AS admins 
            WHERE admins.source_id = recurs.id AND admins.geom IS NOT NULL
            GROUP BY root_id
            '''.format(
                        child_ids='('+','.join(map(str,child_ids))+')',
                        sources_table=AdminSource._meta.db_table,
                        admin_table=Admin._meta.db_table,
                        )
        )

        # create id stats lookup
        stats_lookup = {}
        for row in curs.fetchall():
            child_id = row[0]
            row_stats = {'admin_count':row[1]}
            stats_lookup[child_id] = row_stats
            
        # create child,stats list
        child_stats = [(ch,stats_lookup.get(ch.pk, {})) for ch in children]
        return child_stats

    def all_children(self):
        sources = AdminSource.objects.raw('''
            WITH RECURSIVE recurs AS
            (
                SELECT id FROM {sources_table} WHERE id = {root_id}

                UNION ALL

                SELECT s.id FROM recurs
                INNER JOIN {sources_table} AS s
                ON s.parent_id = recurs.id
            )
            SELECT id FROM recurs
            '''.format(
                        root_id=self.pk,
                        sources_table=AdminSource._meta.db_table,
                        )
        )
        return sources

    def all_admins(self):
        sources = self.all_children()
        source_ids = [s.id for s in sources]
        admins = Admin.objects.exclude(
            geom=None,
        ).filter(
            source__in=source_ids,
        )
        return admins

    # def toplevel_geojson(self):
    #     toplevel = self.admins.filter(geom__isnull=False) # parent=None
    #     #print(toplevel.count())
    #     toplevel_sql = toplevel.query

    #     from django.db import connection
    #     import json
    #     cur = connection.cursor()
    #     sql = f'select id, st_asbinary(st_envelope(geom)) as geom from ({toplevel_sql}) as sub'
    #     #sql = f'select id, st_asbinary(st_simplify(geom, 0.1)) as geom from ({toplevel_sql}) as sub'
    #     #sql = f'select id, st_asgeojson(st_simplify(geom, 0.1)) as geom from ({toplevel_sql}) as sub'
    #     cur.execute(sql)

    #     feats = []
    #     from .geometry import WKBGeometry
    #     for id,geom in cur:
    #         try:
    #             # NOTE: the geom simplify might break the geom and result in None values
    #             geom = WKBGeometry(geom).__geo_interface__
    #             #geom = json.loads(geom)
    #             info = {} #admin.serialize(geom=True)
    #             feat = {'type':'Feature', 'properties':info, 'geometry':geom}
    #             feats.append(feat)
    #         except:
    #             print('feature error:', traceback.format_exc())

    #     # feats = []
    #     # for admin in toplevel:
    #     #     try:
    #     #         info = {} #admin.serialize(geom=True)
    #     #         geom = admin.geom #info.pop('geom')
    #     #         feat = {'type':'Feature', 'properties':info, 'geometry':geom}
    #     #         feats.append(feat)
    #     #     except:
    #     #         print('feature error:', traceback.format_exc())

    #     coll = {'type':'FeatureCollection', 'features':feats}
    #     return coll

    def get_all_parents(self, include_self=True):
        '''Returns a list of all parents, starting with and including self.'''
        refs = [self]
        cur = self
        while cur.parent:
            cur = cur.parent
            refs.append(cur)
        return refs

    def get_all_parents_reversed(self, include_self=True):
        return reversed(self.get_all_parents(include_self))

    def imports_all(self):
        sources = self.all_children()
        from adminImporter.models import DatasetImporter
        source_ids = [s.id for s in sources]
        importers = DatasetImporter.objects.filter(
            source__in=source_ids,
        )
        return importers

        # OLD: too slow
        # # if has child sources, recursively fetch all importers defined on any child sources
        # if self.children.all().count():
        #     for src in self.children.all():
        #         if importers:
        #             _importers = src.imports_all(importers, filters=filters)
        #             importers = importers.union(_importers)
        #         else:
        #             importers = src.imports_all(filters=filters)
            
        # # otherwise fetch importers defined on this sources
        # else:
        #     if filters:
        #         importers = self.importers.filter(**filters)
        #     else:
        #         importers = self.importers.all()

        # return importers

    # def imports_pending(self):
    #     if not hasattr(self, '_imports_pending'):
    #         filters = {'import_status': "Pending"}
    #         self._imports_pending = self.imports_all(filters=filters)
    #     return self._imports_pending

    # def imports_processed(self):
    #     if not hasattr(self, '_imports_processed'):
    #         filters = {'import_status__in': ["Imported","Failed"]}
    #         self._imports_processed = self.imports_all(filters=filters)
    #     return self._imports_processed

    # def imports_failed(self):
    #     if not hasattr(self, '_imports_failed'):
    #         filters = {'import_status': "Failed"}
    #         self._imports_failed = self.imports_all(filters=filters)
    #     return self._imports_failed
