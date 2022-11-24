# from itertools import combinations
# from re import L
# from django.db import models, transaction

# from changeManager.models import BoundaryReference, BoundarySnapshot, BoundaryName, Event

# import json

# # Create your models here.

# class MapDigitizer(models.Model):
#     source = models.OneToOneField("changeManager.BoundarySource", related_name='digitizer', on_delete=models.PROTECT)
#     digitized_data = models.JSONField(blank=True, null=True)
#     last_digitized = models.DateTimeField(null=True, blank=True)

#     @property
#     def digitized_data_json(self):
#         return json.dumps(self.digitized_data)

#     @property
#     def polygonized_data_json(self):
#         refs = self.source.boundary_refs.all()
#         # turn into list of features
#         feats = []
#         for ref in refs:
#             ref = ref.serialize()
#             snaps = ref.pop('snapshots', None)
#             if snaps:
#                 geom = snaps[0]['geom']
#             else:
#                 geom = None
#             props = ref
#             feat = {'type':'Feature',
#                     'properties':props,
#                     'geometry':geom}
#             feats.append(feat)
#         return json.dumps(feats)

#     # def build(self):
#     #     # find all existing snapshots
#     #     old_snapshots = BoundarySnapshot.objects.filter(boundary_ref__source=self.source)
#     #     # polygonize the digitized data
#     #     print('polygonize')
#     #     data = self.digitized_data
#     #     level_lines = [data[lvl] for lvl in sorted(data.keys())] # convert to list
#     #     for lvl,polys in self.iter_split_polygons(poly, level_lines):
#     #         for poly,childre

#     #     level_geoms = self.polygonize(level_lines)
#     #     # build these as snapshots
#     #     print('build snapshots')
#     #     from datetime import date
#     #     start,end = date.today(),date.today()
#     #     event = Event(date_start=start, date_end=end)
#     #     outdated_snapshots = []
#     #     new_snapshots = []
#     #     for lvl,geoms in level_geoms.items():
#     #         for geom in geoms:
#     #             ref = BoundaryReference(source=self.source, level=lvl)
#     #             snapshot = BoundarySnapshot(event=event, boundary_ref=ref, geom=geom.__geo_interface__)
#     #             # detect if snapshot modifies any existing ones
#     #             # ie intersects but area1 != area2
#     #             # mark old ones for deletion
#     #             #outdated_snapshots.extend()
#     #             # mark this snapshot for saving
#     #             new_snapshots.append(snapshot)

#     #     print('saving')
#     #     with transaction.atomic():
#     #         # save new snapshots
#     #         BoundarySnapshot.objects.bulk_create(new_snapshots)

#     #         # delete outdated snapshots
#     #         # ...

#     # def iter_split_polygons(self, polygon, line_levels, level=0):
#     #     'Recursively take a pol'
#     #     from shapely.geometry import shape
#     #     from shapely.ops import polygonize, split

#     #     data = sorted(data.items(), key=lambda item: item[0]) # convert to list
#     #     for lvl in range(len(data)):
#     #         # polygonize current level
#     #         lvl,lines = data[lvl]
#     #         lines = [shape(line) for line in lines]
#     #         geoms = polygonize(lines)

#     #     for lvl,lines in data.items():
#     #         lines = [shape(line) for line in lines]
#     #         geoms = polygonize(lines)
#     #         yield lvl,geoms

#     # def split_polygon(self, polygon, split_lines):
#     #     'Split a polygon by a list of split_lines.'
#     #     from shapely.ops import polygonize, split
#     #     geoms = split(polygon, split_lines)
#     #     polys = [geom for geom in geoms if 'Polygon' in geom.geom_type]
#     #     return polys

#     def build(self):
#         # find all existing snapshots
#         old_snapshots = BoundarySnapshot.objects.filter(boundary_ref__source=self.source)
#         # polygonize the digitized data
#         print('polygonize')
#         data = self.digitized_data
#         level_colls = self.polygonize(data)
#         # build these as snapshots
#         print('build snapshots')
#         start = self.source.valid_from
#         end = self.source.valid_to
#         event = Event(date_start=start, date_end=end)
#         outdated_snapshots = []
#         new_snapshots = []
#         def find_parent(geom, candidates):
#             for i,cand in enumerate(candidates):
#                 # NOT VERY EFFICIENT! 
#                 if cand.intersects(geom) and cand.intersection(geom).area > 0:
#                     return i
#         level_refs = {}
#         for lvl,coll in level_colls.items():
#             refs = level_refs[lvl] = []
#             for geom in coll.geoms:
#                 if lvl == 'ADM0':
#                     parent = None
#                 else:
#                     parent_lvl = f'ADM{int(lvl[-1])-1}'
#                     candidates = level_colls[parent_lvl].geoms
#                     parent_i = find_parent(geom, candidates)
#                     if parent_i is None:
#                         # what to do with parts that dont belong to any parent? 
#                         # for now just allow, though will probably break something
#                         parent = None
#                     else:
#                         parent = level_refs[parent_lvl][parent_i]
                    
#                 ref = BoundaryReference(parent=parent, source=self.source, level=int(lvl[-1]))
#                 refs.append(ref)
#                 snapshot = BoundarySnapshot(event=event, boundary_ref=ref, geom=geom.__geo_interface__)
#                 # detect if snapshot modifies any existing ones
#                 # ie intersects but area1 != area2
#                 # mark old ones for deletion
#                 #outdated_snapshots.extend()
#                 # mark this snapshot for saving
#                 new_snapshots.append(snapshot)

#         print('saving')
#         with transaction.atomic():
#             # delete all previous
#             self.source.boundary_refs.all().delete()

#             # save event
#             event.save()

#             # save new boundary refs
#             #new_refs = [s.boundary_ref for s in new_snapshots]
#             #BoundaryReference.objects.bulk_create(new_refs)
#             for s in new_snapshots:
#                 s.boundary_ref.save()

#             # save new snapshots
#             BoundarySnapshot.objects.bulk_create(new_snapshots)

#             # delete outdated snapshots
#             # ...

#     def polygonize(self, data):
#         from shapely.geometry import shape, LineString, MultiLineString, GeometryCollection
#         from shapely.ops import split, polygonize, polygonize_full, unary_union
#         from itertools import combinations
#         level_colls = {}
#         cumul_lines = []
#         for lvl,coll in data.items():
#             print(lvl,coll)
#             # each level considers the lines of all levels above itself
#             cumul_lines.extend( [line
#                                 for multiline in coll['geometries'] 
#                                 for line in multiline['coordinates']] )
#             # shapely polygonize only connects lines that touch at the ends.
#             # use unary_union to split apart a self-intersecting line into 
#             # parts that touch at the ends.
#             cumul_line_parts = unary_union(MultiLineString(cumul_lines))
#             # then polygonize
#             (polygons,dangles,cut_edges,invalid_rings) = polygonize_full(cumul_line_parts)
#             coll = polygons
#             print(coll)
#             level_colls[lvl] = coll

#             # cumul_lines.extend( [LineString(line)
#             #                     for multiline in coll['geometries'] 
#             #                     for line in multiline['coordinates']] )
#             # print(cumul_lines)
#             # if len(cumul_lines) == 1:
#             #     print('UNARY',unary_union(cumul_lines[0]))
#             #     polys = list(polygonize(unary_union(cumul_lines[0])))
#             #     coll = GeometryCollection(polys)
#             # else:
#             #     cumul_line_parts = []
#             #     for line1,line2 in combinations(cumul_lines, 2):
#             #         parts = split(line1, line2)
#             #         cumul_line_parts.extend(parts.geoms)
#             #     print(cumul_line_parts)
#             #     (polygons,dangles,cut_edges,invalid_rings) = polygonize_full(cumul_line_parts)
#             #     coll = polygons
#             # print(coll)
#             # level_colls[lvl] = coll

#         return level_colls

#     def update_names(self, data):
#         with transaction.atomic():
#             for pk,names in data.items():
#                 ref = BoundaryReference.objects.get(pk=pk)
#                 # clear old names
#                 ref.names.clear()
#                 # add new names
#                 for name in names:
#                     name,created = BoundaryName.objects.get_or_create(name=name)
#                     ref.names.add(name)
#                 # save
#                 ref.save()

