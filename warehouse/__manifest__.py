{
    'name': "仓库管理",

    'summary': """
       仓库物料管理。。。""",

    'description': """
        深圳市神州动力数码有限公司
    """,

    'author': "zspdc",
    'website': "http://www.szpdc.com",

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/warehouse_security.xml',
        'security/warehouse_rule.xml',
        'security/ir.model.access.csv',
        'views/add_button.xml',
        'views/model_menus.xml',
        'views/model_views.xml',
        # 'views/random_number.xml',
        'views/timing_task.xml',
    ],
    'qweb': [
        'static/src/xml/tree_button.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'application': True,
    'sequence': 4,
}
