{
    'name': 'Addons: Reload Demo Data',
    'description': 'Helper to reload demo-data from installed modules',
    'author': 'LTrThanh',
    'depends': [
        'base',
        'mail',
    ],
    'application': False,
    'version': '18.0.0.0.0',
    'license': 'AGPL-3',
    'support': 'ltrthanh.dev@gmail.com',
    'installable': True,
    'data': [
        # security
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        # views
        'views/reload_missing_data_session_views.xml',

    ],
    'assets': {

    },
    'images': ['static/description/icon.png'],
}
