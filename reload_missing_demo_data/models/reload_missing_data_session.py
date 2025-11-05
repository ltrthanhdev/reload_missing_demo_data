import logging
import os

from odoo import models, fields, api, _, SUPERUSER_ID, modules
from odoo.exceptions import UserError, ValidationError
from odoo.tools import convert_file
from odoo.modules import module as module_loader
from odoo.modules.graph import Graph

_logger = logging.getLogger(__name__)


class ReloadMissingDataSession(models.Model):
    _name = "reload.missing_data.session"
    _inherit = [
        'mail.thread', 'mail.activity.mixin'
    ]
    _description = "Reload Missing-data demo Session"
    _rec_names_search = [
        'user_id',
        'trigger_time',
        'module_name',
    ]

    active = fields.Boolean(
        string="Can invoke",
        default=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Invoker",
        help="The user who invoke action reloading missing demo-data",
        default=lambda self: self.env.user.id,
    )
    trigger_time = fields.Datetime(
        string="Invoked time",
    )
    module_name = fields.Char(
        string="Module's name to load",
    )

    def _get_demo_data_to_load(self):
        def _get_dependencies(root_module, accumulator, root_modules):
            for dep in root_module.dependencies_id:
                dep_mod = root_modules.filtered(lambda im: im.name == dep.name)
                if dep_mod and dep_mod.name not in accumulator:
                    accumulator.append(dep_mod.name)
                    _get_dependencies(root_module=dep_mod, accumulator=accumulator, root_modules=root_modules)
            return accumulator

        installed_modules = self.env['ir.module.module'].sudo().search(
            domain=[('state', '=', 'installed')]
        )
        if self.module_name:
            target_module = installed_modules.filtered(lambda im: im.name == self.module_name)
            target_dependencies = _get_dependencies(
                root_module=target_module, accumulator=[self.module_name], root_modules=installed_modules
            )
            installed_modules = installed_modules.filtered(lambda im: im.name in target_dependencies)

        installed_module_names = set(installed_modules.mapped('name'))

        graph = Graph()
        graph.add_modules(cr=self.env.cr, module_list=installed_module_names)
        sorted_module_names = [node.name for node in graph if node.name in installed_module_names]

        to_load = dict()
        for sorted_module_name in sorted_module_names:
            module_manifest = module_loader.load_manifest(module=sorted_module_name)
            demo_file_paths = module_manifest.get('demo', [])
            if not demo_file_paths:
                continue
            _logger.info(msg=f"\n➡️  Reloading demo-data from module: {sorted_module_name}")
            to_load[sorted_module_name] = demo_file_paths
        return to_load

    def _action_load_demo_data(self, to_load):
        for module_name, demo_data_paths in to_load.items():
            module_path = modules.get_module_path(module_name)
            for demo_data_path in demo_data_paths:
                file_path = os.path.join(module_path, demo_data_path)
                if not os.path.isfile(file_path):
                    _logger.exception(msg=f"⚠️ Demo-data path not valid: {file_path}")
                    continue

                _logger.info(msg=f"🔹 Loading demo: {module_name}/{demo_data_path}")
                with self.env.cr.savepoint():
                    env_with_demo = self.env(context=dict(self.env.context, load_demo=True))
                    try:
                        convert_file(
                            env_with_demo,
                            module_name,
                            file_path,
                            None,
                            mode="init",
                            kind="demo",
                            noupdate=True,
                        )
                    except Exception as e:
                        exception_msg = f"⚠️ Skipped loading demo from {file_path} due to occurring terrible error: {e}"
                        _logger.exception(msg=exception_msg)
                        self.message_post(
                            body=exception_msg,
                            message_type="notification",
                        )
                self.env.cr.commit()
                _logger.info(msg=f"✅ Loading OKAY 👍🏼👍🏼👍🏼👍🏼👍🏼: {module_name}/{demo_data_path}")

    def action_reload_demo_data(self):
        try:
            # only trigger on an active session
            self = self.filtered(lambda ds: ds.active)
            self.ensure_one()
        except ValueError:
            return self
        # main flow
        to_load = self._get_demo_data_to_load()
        if not to_load:
            return self
        self._action_load_demo_data(to_load=to_load)
        # update references
        self.trigger_time = fields.Datetime.now()
        self.user_id = self.env.user.id
        self.action_archive()
        return self

    def action_unarchive(self):
        cant_unarchive = self.filtered(lambda ds: ds.trigger_time)
        can_unarchive = self.filtered(lambda ds: not ds.trigger_time)

        if cant_unarchive:
            raise UserError(_("Cant archive triggered session."))

        return super(ReloadMissingDataSession, can_unarchive).action_unarchive()

    @api.depends('module_name', 'user_id', 'trigger_time')
    def _compute_display_name(self):
        for data_session in self:
            display_name = data_session.module_name
            if not display_name:
                display_name = _("Reload Data Session")
            data_session.display_name = display_name
