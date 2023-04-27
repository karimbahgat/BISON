
from .models import Admin, AdminSource
from adminImporter.models import DatasetImporter

def sources_with_stats(source_ids):
    # NOTE: this is very messy and maybe not the best approach
    from django.db import connection
    curs = connection.cursor()

    # exit early? 
    if not source_ids:
        return []

    # custom aggregation with group by
    sql = '''
    WITH RECURSIVE sources AS
    (
        SELECT id, id AS root_id
        FROM {sources_table} WHERE id IN {source_ids}

        UNION ALL

        SELECT s.id,sources.root_id FROM sources
        INNER JOIN {sources_table} AS s
        ON s.parent_id = sources.id
    ),
    importers AS
    (
        SELECT sources.root_id,
                imports.status_updated,
                (CASE WHEN imports.import_status = 'Imported' THEN 1 ELSE 0 END) AS imported,
                (CASE WHEN imports.import_status = 'Pending' THEN 1 ELSE 0 END) AS pending,
                (CASE WHEN imports.import_status = 'Failed' THEN 1 ELSE 0 END) AS failed,
                (CASE WHEN imports.import_status = 'Importing' THEN 1 ELSE 0 END) AS importing
        FROM sources
        INNER JOIN {imports_table} AS imports 
        WHERE imports.source_id = sources.id
    )
    SELECT root_id, SUM(imported), SUM(pending),
                    SUM(failed), SUM(importing), MAX(status_updated)
    FROM importers
    GROUP BY root_id
    '''.format(
                sources_table=AdminSource._meta.db_table,
                imports_table=DatasetImporter._meta.db_table,
                source_ids='('+','.join(map(str,source_ids))+')',
                )
    print(sql)
    curs.execute(sql)

    # create id stats lookup
    print('calc stats')
    stats_lookup = {}
    for row in curs:
        child_id,imported,pending,failed,importing,updated = row
        row_stats = {'status_counts': {'Imported':imported, 'Pending':pending, 
                                        'Failed':failed, 'Importing':importing},
                    'status_latest':updated}
        stats_lookup[child_id] = row_stats
        
    # create child,stats list
    print('getting children')
    sources = AdminSource.objects.filter(id__in=source_ids)
    source_stats = [(s,stats_lookup.get(s.pk, {})) for s in sources]
    return source_stats
