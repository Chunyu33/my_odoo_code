# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
import random


class House(models.Model):
    _name = 'warehouse.house'
    _description = '仓库表'

    name = fields.Char(string='仓库名')
    type_name_ids = fields.Many2many('warehouse.category', string='分类')
    admin = fields.Many2one('res.users', string='管理员')
    materials = fields.Many2many('warehouse.material', string='物料明细')

    # 同步库存物料明细
    @api.model
    def synchronous_materials(self):
        try:
            all_house = self.sudo().search([])
            all_materials = self.sudo().env['warehouse.material'].search([])
            materrial_ids = []
            for house in all_house:
                for item in all_materials:
                    if item.house.id == house.id:
                        materrial_ids.append(item.id)
                for item in all_materials:
                    if item.house.id == house.id:
                        house.materials = [(6, 0, materrial_ids)]
                        materrial_ids.clear()
                        break
        except exceptions.ValidationError as err:
            raise err


class Category(models.Model):
    _name = 'warehouse.category'
    _description = '分类表'

    name = fields.Char(string='分类名')
    switch_serial = fields.Boolean(string='序列号开关')


class Material(models.Model):
    _name = 'warehouse.material'
    _description = '物料管理表'

    # 随机生成物料编码
    @api.model
    def generate_code(self):
        fixed_str = 'SZPDC'
        result = fixed_str + str(random.randint(1, 1e5))
        return result

    name = fields.Char(string='物料名称')
    code = fields.Char(string='物料编码', readonly=True, default=generate_code)
    serial_numbers = fields.Many2many('warehouse.serial', string='序列号')
    max_number = fields.Integer(string='库存数量')
    unit_price = fields.Float(string='单价')
    house = fields.Many2one('warehouse.house', string='所属仓库')
    reservation_num = fields.Integer(string='预定数量', default=0)
    actual_num = fields.Integer(string='实际出库', default=0)
    user = fields.Many2one('res.users', string='用户', default=lambda self: self.env.user)
    original_house_id = fields.Char(string='原物料id')

    # 根据库存数量生成序列号
    @api.onchange('max_number')
    def generate_serial_by_max_number(self):
        num = len(self.serial_numbers)
        count = self.max_number
        # 如果管理员录入的库存数量大于原来的，序列号在原来的基础上增加到库存相应的数量
        if count > num:
            new_count = count - num
            while new_count > 0:
                serial = str(random.randint(1, 1e6))
                all_record = self.env['warehouse.serial'].search([])
                if all_record:
                    for i in all_record:
                        # 如果序列号重复，重新生成一个
                        if i.serial_number == serial:
                            serial = str(random.randint(1, 1e6))
                # 生成序列号
                self.sudo().env['warehouse.serial'].create({
                    'serial_number': serial,
                    'code': self.code,
                    'state': 'inventory',
                    'name': self.name,
                })
                new_count -= 1
            # 在对应编码的物品里面写入生成的序列号
            ids = []
            serials = self.env['warehouse.serial'].search([('code', '=', self.code)])
            for i in serials:
                ids.append(i.id)
            self.serial_numbers = [(6, 0, ids)]
            return
        # 如果输入的数量小于原来的， 删除差数数量，更新
        if count < num:
            count = num - count
            serials = self.env['warehouse.serial'].search([('code', '=', self.code)])
            serial_ids = []
            for i in serials:
                serial_ids.append(i.id)
            for sid in serial_ids:
                if count >= 1:
                    sql = 'delete from warehouse_serial where id = {}'.format(sid)
                    self.env.cr.execute(sql)
                    self.env.cr.commit()
                    count -= 1
                if count < 1:
                    break
            return
        # 原库存和重新录入的数量一致，不做额外处理
        if count == num:
            return

    @api.constrains('max_number')
    def validate_max_number(self):
        if self.max_number < 0:
            raise exceptions.ValidationError('输入有误！')


class Approval(models.Model):
    _name = 'warehouse.approval'
    _description = '物料审批'

    name = fields.Many2one(comodel_name='warehouse.material', string='物料')
    code = fields.Char(string='物料编码',)
    serial_numbers = fields.Many2many('warehouse.serial', 'id', string='序列号')
    apply_number = fields.Integer(string='申请数量')
    surplus_number = fields.Integer(string='剩余数量',)
    type = fields.Selection([
        ('borrow', '借出'),
        ('back', '归还'),
    ], string='类型')
    state = fields.Selection([
        ('put', '入库'),
        ('out', '出库'),
        ('refused', '拒绝'),
        ('done', '完成'),
    ], string='审批状态', readonly=True)
    apply_user = fields.Many2one('res.users', string='申请人', default=lambda self: self.env.user, readonly=True)
    department_id = fields.Many2many('warehouse.department', string='部门', default=lambda self: self.env.user.department,
                                     readonly=True)

    @api.model
    def create(self, values):
        for item in self.name.house.type_name_ids:
            if item.switch_serial is True:
                raise exceptions.UserError('该物料需要填写序列号！')
        else:
            return super(Approval, self).create(values)

    # 填写归还数量
    @api.multi
    def button_back_num(self):
        data = {
            'id': self.id,
            'material': self.name,
            'type': self.type,
            'record': self,
        }
        return {
            'name': '填写数量',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('warehouse.warehouse_number_view_form').id,
            'target': 'new',
            'res_model': 'warehouse.number',
            'context': {'data': data},
            'domain': '[]'
        }

    # 填写序列号
    @api.multi
    def input_serial(self):
        data = self.id
        return {
            'name': '填写序列号',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('warehouse.warehouse_input_view_form').id,
            'target': 'new',
            'res_model': 'warehouse.input',  # 引用的模型
            'context': {'data': data},  # 上下文值
            'domain': '[]'
        }

    # 分类仓库按钮为false时，不需要匹配序列号情况的出库方法
    @api.onchange('apply_number')
    def do_not_with_serial(self):
        if self.apply_number > self.name.max_number:
            raise exceptions.ValidationError('申请数量不得大于库存数量！')
        if self.type == 'back':
            pass
        for item in self.name.house.type_name_ids:
            if item.switch_serial is True:
                raise exceptions.UserError('该物料需要填写序列号！')
        if self.apply_number != 0:
            # 获取申请数量
            count = self.apply_number
            if count > len(self.serial_numbers):
                count = count - len(self.serial_numbers)
            if count < len(self.serial_numbers):
                raise exceptions.UserError('不支持此操作！')
            if count == len(self.serial_numbers):
                return
            # 获取物料的编码
            code_num = self.name.code
            # material_name = self.name.name
            # 通过编码获取出相同物料种类的所有序列号
            serials = self.sudo().env['warehouse.serial'].search([('code', '=', code_num)])
            print('serials:', serials)
            serial_ids = []
            # 根据申请数量取出同等数量的序列号
            for item in serials:
                if count == 0:
                    break
                else:
                    serial_ids.append(item.id)
                    count -= 1
            # 把取出的序列号的数据分别存储到两个列表中
            serial_numbers = []
            names = []
            codes = []
            for item in serial_ids:
                tmp_serial = self.sudo().env['warehouse.serial'].search([('id', '=', item)])
                serial_numbers.append(tmp_serial.serial_number)
                names.append(tmp_serial.name)
                codes.append(tmp_serial.code)
            # 删除取出库存的序列号
            for i in serial_ids:
                sql = 'delete from warehouse_serial where id = {}'.format(i)
                self.sudo().env.cr.execute(sql)
                self.sudo().env.cr.commit()
            # 库存物料数量发生变化
            material = self.sudo().env['warehouse.material'].search([('code', '=', code_num)])
            material.sudo().write({
                'max_number': material.max_number - self.apply_number,  # 库存=原库存-申请数
                'reservation_num': material.reservation_num + self.apply_number,  # 预定数量=申请数
            })
            # 把取出的数据重新创建序列号(接触与库存的关联)并且关联到当前的记录上
            new_serial_ids = []
            this_all_serials = self.serial_numbers
            if this_all_serials:
                for j in this_all_serials:
                    new_serial_ids.append(j.id)
            for i in range(len(serial_numbers)):
                self.sudo().env['warehouse.serial'].create({
                    'name': self.name.name,
                    'serial_number': serial_numbers[i],
                    'code': self.name.code,
                    'state': 'wait_out',
                    'user': self.env.user.id,
                })
                # 创建完成后直接搜索，取出id
                tmp2_serial = self.sudo().env['warehouse.serial'].search([('serial_number', '=', serial_numbers[i])])
                new_serial_ids.append(tmp2_serial.id)
            # 自动填充值
            print(self.id, self.name.code, material.max_number)
            # 自动填写编码
            self.code = self.name.code
            # 计算剩余数量
            self.surplus_number = material.max_number
            # 更新关联
            self.sudo().serial_numbers = [[6, 0, new_serial_ids]]
            # self.sudo().write({'code': code_num, 'surplus_number': material.max_number})     # 确保序列号正确写入
        else:
            return

    # 提交审批
    def button_confirm(self):
        if self.type == 'borrow':
            if len(self.serial_numbers) < 1 and self.state == 'refused':
                raise exceptions.ValidationError('此条记录已作废，请重新填写表单！')
            else:
                if len(self.serial_numbers) < 1:
                    raise exceptions.ValidationError('请选择相应数量的序列号！')
                else:
                    self.sudo().state = 'out'
        if self.type == 'back':
            self.sudo().state = 'put'

    # 获取具有审批权限的用户
    @api.model
    def get_security_users(self):
        manager_groups = self.env['res.groups'].search([('name', '=', '仓库管理员')]).users
        dep_manager_groups = self.env['res.groups'].search([('name', '=', '部门经理')]).users
        manager_ids = []
        dep_manager_ids = []
        for i in dep_manager_groups:
            dep_manager_ids.append(i.id)
        for j in manager_groups:
            manager_ids.append(j.id)
        return manager_ids, dep_manager_ids

    # 批量审批 通过
    @api.model
    def to_agree(self, **args):
        user_id = self.env.user.id
        managers, dep_managers = self.get_security_users()
        if user_id in managers or user_id in dep_managers:
            approvals = []
            approval_ids = self._context.get('ids')
            if approval_ids is None:
                return
            for i in approval_ids:
                approvals.append(self.env['warehouse.approval'].search([('id', '=', i)]))
            for item in approvals:
                self.agreed_the_request(item)
        else:
            raise exceptions.UserError('只有管理员、部门经理才能进行审批')

    # 批量审批 拒绝
    @api.model
    def to_refuse(self):
        user_id = self.env.user.id
        managers, dep_managers = self.get_security_users()
        if user_id in managers or user_id in dep_managers:
            approvals = []
            approval_ids = self._context.get('ids')
            if approval_ids is None:
                return
            for i in approval_ids:
                approvals.append(self.env['warehouse.approval'].search([('id', '=', i)]))
            for item in approvals:
                self.reject_the_request(item)
        else:
            raise exceptions.UserError('只有管理员、部门经理才能进行审批')

    # 通过审批
    @api.multi
    def agreed_the_request(self, record):
        if record.state == 'done' or record.state == 'refused':
            return
        try:
            # 如果是出库申请
            if record.type == 'borrow':
                try:
                    # 物料数据变更
                    material = record.env['warehouse.material'].search([('id', '=', record.name.id)])
                    # 审批记录标记完成
                    record.sudo().write({
                        'state': 'done',
                    })
                    # 当前记录的序列号标记为 已出库
                    serials = record.serial_numbers
                    for item in serials:
                        item.sudo().write({'state': 'outbound'})
                    tmp_serials = record.env['warehouse.serial'].search([('code', '=', record.code)])
                    actual_num = 0
                    for i in tmp_serials:
                        if i.state == 'outbound':
                            actual_num += 1
                    # 计算实际出库， 申请数清零
                    material.sudo().write({
                        'actual_num': actual_num,
                        'reservation_num': 0,
                    })
                    # 数据写入记录表
                    name = record.name.name
                    code = record.code
                    type = record.type
                    number = record.apply_number
                    sum_price = record.name.unit_price * record.apply_number
                    if record.type == 'borrow':
                        out_time = fields.Datetime.now()
                        back_time = None
                    else:
                        back_time = fields.Datetime.now()
                        out_time = None
                    user = record.apply_user
                    data = {
                        'name': name,
                        'code': code,
                        'type': type,
                        'number': number,
                        'sum_price': sum_price,
                        'out_time': out_time,
                        'back_time': back_time,
                        'user': user.id,
                    }
                    record.sudo().env['warehouse.record'].create(data)
                    # 创建申请人的物料
                    ids = []
                    user_id = None
                    uname = ''
                    for i in record.serial_numbers:
                        ids.append(i.id)
                        user_id = i.user.id
                        uname = i.user.name
                    user_materials = self.sudo().env['warehouse.material'].search([('user', '=', user_id)])
                    for user_ma in user_materials:
                        if user_ma.code == code:
                            for i in user_ma.serial_numbers:
                                ids.append(i.id)
                    user_data = {
                        'name': name + '-' + uname,
                        'code': code,
                        'serial_numbers': [[6, 0, ids]],
                        'max_number': number,
                        'house': record.name.house.id,
                        'user': user_id,
                        'original_house_id': record.name.id,
                    }
                    if user_materials:
                        for user_ma in user_materials:
                            if user_ma.code == code:
                                user_ma.sudo().write(user_data)
                                user_ma.sudo().write({'max_number': len(user_ma.serial_numbers)})
                            else:
                                self.sudo().env['warehouse.material'].create(user_data)
                    else:
                        self.sudo().env['warehouse.material'].create(user_data)
                except exceptions.ValidationError as err:
                    raise err
            # 如果是归还申请
            if record.type == 'back':
                try:
                    # 把申请的物料还回原来的地方
                    original_material = self.sudo().env['warehouse.material'].search(
                        [('id', '=', record.name.original_house_id)])
                    all_serial_ids = []
                    for i in original_material.serial_numbers:
                        all_serial_ids.append(i.id)
                    for j in record.serial_numbers:
                        j.state = 'inventory'
                        j.user = None
                        all_serial_ids.append(j.id)
                    # 把物料序列号还回去
                    original_material.sudo().write({
                        'serial_numbers': [[6, 0, all_serial_ids]],
                        'max_number': len(all_serial_ids),
                    })
                    # 如果记录的库存为0，删除
                    user_material = self.sudo().env['warehouse.material'].search([('id', '=', record.name.id)])
                    if len(user_material.serial_numbers) == 0:
                        sql = 'delete from warehouse_material where id = {}'.format(record.name.id)
                        record.env.cr.execute(sql)
                        record.env.cr.commit()
                    # 当前申请记录标记为完成
                    record.state = 'done'
                    # 生成借还记录
                    new_name = record.name.name
                    new_code = record.code
                    new_type = record.type
                    new_number = record.apply_number
                    new_sum_price = record.name.unit_price * record.apply_number
                    if record.type == 'back':
                        new_out_time = None
                        new_back_time = fields.Datetime.now()
                    else:
                        new_back_time = None
                        new_out_time = fields.Datetime.now()
                    user = record.apply_user
                    data = {
                        'name': new_name,
                        'code': new_code,
                        'type': new_type,
                        'number': new_number,
                        'sum_price': new_sum_price,
                        'out_time': new_out_time,
                        'back_time': new_back_time,
                        'user': user.id,
                    }
                    record.sudo().env['warehouse.record'].create(data)
                    # 删除物料
                except exceptions.ValidationError as err:
                    raise err
            else:
                return
        except exceptions.ValidationError as err:
            raise err

    # 驳回
    @api.multi
    def reject_the_request(self, record):
        # 已通过的记录不能驳回
        if record.state == 'done':
            raise exceptions.ValidationError('已通过的记录不能再驳回')
        elif record.state == 'refused':
            return
        else:
            # 如果是借出，需要把库存中预订的物料退回
            if record.type == 'borrow':
                try:
                    # 序列号先存储到变量中，解除关联
                    serial_ids = []
                    back_code = record.code  # 物料编码
                    serial_numbers = []  # 当前申请的序列号
                    serials = record.serial_numbers
                    for item in serials:
                        serial_ids.append(item.id)
                        serial_numbers.append(item.serial_number)
                    for id in serial_ids:
                        sql = 'delete from warehouse_serial where id = {}'.format(id)
                        record.env.cr.execute(sql)
                        record.env.cr.commit()
                    for serial_num in serial_numbers:
                        record.sudo().env['warehouse.serial'].create(
                            {'serial_number': serial_num, 'code': back_code, 'state': 'inventory',
                             'name': record.name.name, })
                    # 物料重新关联上对应的序列号
                    all_serials = record.env['warehouse.serial'].search([('code', '=', back_code)])
                    new_serial_ids = []
                    for item in all_serials:
                        new_serial_ids.append(item.id)
                    # 物料库存回退
                    material = record.env['warehouse.material'].search([('code', '=', record.code)])
                    # 进行关联
                    material.serial_numbers = [[6, 0, new_serial_ids]]
                    reservation_num = material.reservation_num - len(record.serial_numbers)
                    if reservation_num < 0:
                        reservation_num = 0
                    # 库存物料数量发生变更
                    material.sudo().write(
                        {'max_number': len(new_serial_ids),
                         'reservation_num': reservation_num})
                    # 当前记录状态变更为拒绝，记录作废
                    record.state = 'refused'
                except exceptions.ValidationError as err:
                    raise err
            # 如果是归还物料,只是变更一下状态,入库的时候可重复提交
            if record.type == 'back':
                if record.sudo().state == 'refused':
                    return
                if record.sudo().state == 'done':
                    raise exceptions.ValidationError('审批已经通过，不支持此操作')
                else:
                    record.sudo().state = 'refused'


class Serial(models.Model):
    _name = 'warehouse.serial'
    _description = '序列号'

    serial_number = fields.Char(string='序列号')
    name = fields.Char(string='物料名')
    code = fields.Char(string='编码', readonly=True)
    state = fields.Selection([
        ('outbound', '已出库'),
        ('inventory', '库存'),
        ('wait_out', '待出库'),
        ('wait_in', '待入库'),
    ], string='状态', default='inventory', readonly=True)

    user = fields.Many2one('res.users', string='申请人')


class Record(models.Model):
    _name = 'warehouse.record'
    _description = '借用归还记录表'

    name = fields.Char(string='物料名')
    code = fields.Char(string='物料编码', readonly=True)
    type = fields.Selection([
        ('borrow', '借出'),
        ('back', '归还'),
    ], string='类型')
    number = fields.Integer(string='数量', readonly=True)
    sum_price = fields.Float(string='总价', readonly=True)
    out_time = fields.Datetime(string='借出时间', readonly=True)
    back_time = fields.Datetime(string='归还时间', readonly=True)
    user = fields.Many2one('res.users', string='用户')


class Department(models.Model):
    _name = 'warehouse.department'
    _description = '部门表'

    name = fields.Char(string='部门名称')
    parent_department = fields.Many2one('warehouse.department', string='父部门')


class User(models.Model):
    _inherit = 'res.users'
    _description = '用户表'

    department = fields.Many2many('warehouse.department', string='部门')


class Input(models.TransientModel):
    _name = 'warehouse.input'
    _description = '填写序列号匹配'

    i_serial = fields.Char(string='序列号')

    # 模态框--填写序列号匹配物料申请出库
    @api.multi
    def button_submit(self):
        try:
            # 通过context拿到当前的物料审批记录
            approval_id = self.sudo().env.context.get('data')
            approval = self.sudo().env['warehouse.approval'].search([('id', '=', approval_id)])
            # 取出相应物料的库存情况
            material = self.sudo().env['warehouse.material'].search([('id', '=', approval.name.id)])
            # 判断当前仓库分类是否需要匹配序列号
            house = self.sudo().env['warehouse.house'].search([('id', '=', material.house.id)])
            # 接收当前输入的序列号
            ser_num = self.i_serial
            type_length = 0
            for item in house.type_name_ids:
                if item.switch_serial is False:
                    type_length += 1
            # 如果所有分类开关都是 False
            if type_length == len(house.type_name_ids):
                raise exceptions.ValidationError('这个物料不需要匹配序列号！')
            if approval.type is None:
                raise exceptions.UserError('请选择借出类型！')
            else:
                # 取出相同类型的物料的序列号、物料的编码
                serials = []
                for item in material.serial_numbers:
                    serials.append(item.serial_number)
                # 物料编码
                this_code = material.code
                # 校验输入的序列号是否正确
                if ser_num not in serials:
                    raise exceptions.ValidationError('输入的序列号不正确！')
                else:
                    if approval.type == 'borrow':
                        # 每次匹配到一个物料，申请数量+1
                        approval.apply_number = approval.apply_number + 1
                        # 自动更正物料编码
                        approval.code = this_code
                        # 先用变量保存输入的序列号的记录数据
                        old_serial = self.sudo().env['warehouse.serial'].search([('serial_number', '=', ser_num)])
                        serial_number = old_serial.serial_number
                        code = old_serial.code
                        state = 'wait_out'  # 待出库
                        sql = 'delete from warehouse_serial where id = {}'.format(old_serial.id)
                        self.sudo().env.cr.execute(sql)
                        self.sudo().env.cr.commit()
                        self.sudo().env['warehouse.serial'].create({
                            'name': material.name,
                            'serial_number': serial_number,
                            'code': code,
                            'state': state,
                            'user': self.env.user.id,
                        })
                        # 再把新建的记录关联到物料审批的序列号明细
                        ser_ids = []
                        all_serials = approval.serial_numbers
                        for item in all_serials:
                            ser_ids.append(item.id)
                        new_serial = self.env['warehouse.serial'].search([('serial_number', '=', serial_number)])
                        ser_ids.append(new_serial.id)
                        approval.sudo().serial_numbers = [[6, 0, ser_ids]]
                        # 数量、状态发生相应的变化
                        material.sudo().max_number = material.max_number - 1  # 库存-1
                        material.sudo().reservation_num = approval.apply_number  # 物料预定数量 = 表单申请数量
                        # 计算库存剩余数量
                        approval.sudo().surplus_number = material.max_number
        except exceptions.ValidationError as err:
            raise err


class BackNumber(models.TransientModel):
    _name = 'warehouse.number'
    _description = '填写数量'

    number = fields.Integer(string='数量', default=0)

    def button_number_submit(self):
        data = self.sudo().env.context.get('data')
        if data['type'] != 'back':
            raise exceptions.ValidationError('类型不正确')
        else:
            count = self.number
            current_approval = self.sudo().env['warehouse.approval'].search([('id', '=', data['id'])])  # 当前的审批记录
            serials = self.sudo().env['warehouse.serial'].search(
                [('code', '=', current_approval.name.code)])  # 当前物料的所有序列号
            length = 0
            for i in serials:
                if i.state == 'outbound':
                    length += 1
            if self.number > length:
                raise exceptions.ValidationError('归还数量不可高于申请数量！')
            use_serial_ids = []
            for item in serials:
                if count == 0:
                    break
                if item.state == 'outbound':  # 找出对应已经出库、对应数量的物料序列号
                    use_serial_ids.append(item.id)
                    count -= 1
            # 保存这些序列号数据
            old_serials = []
            old_ids, serial_numbers, names, codes, = [], [], [], []
            for i in use_serial_ids:
                old_serials.append(self.sudo().env['warehouse.serial'].search([('id', '=', i)]))
            for j in old_serials:
                old_ids.append(j.id)
                serial_numbers.append(j.serial_number)
                names.append(j.name)
                codes.append(j.code)
            for id in old_ids:
                sql = 'delete from warehouse_serial where id = {}'.format(id)
                self.sudo().env.cr.execute(sql)
                self.sudo().env.cr.commit()
            for i in range(len(serial_numbers)):
                self.sudo().env['warehouse.serial'].create({
                    'serial_number': serial_numbers[i],
                    'name': names[i],
                    'code': codes[i],
                    'state': 'wait_in',
                    'user': self.env.user.id,
                })
            new_all_serial = self.env['warehouse.serial'].search([('code', '=', current_approval.name.code)])
            surplus_number = 0
            app_serial_ids = []
            for k in new_all_serial:
                if k.state == 'outbound':
                    surplus_number += 1
                if k.state == 'wait_in':
                    app_serial_ids.append(k.id)
            current_approval.sudo().write({
                'apply_number': self.number,
                'code': current_approval.name.code,
                'surplus_number': surplus_number,
                'serial_numbers': [[6, 0, app_serial_ids]]
            })
