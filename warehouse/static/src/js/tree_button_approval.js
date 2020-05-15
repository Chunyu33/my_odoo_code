odoo.define('bicon_wms_base.bicon_list_view_button_approval', function (require) {
    "use strict";
    //这些是调⽤需要的模块
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var ListController = require('web.ListController');
    //这块代码是继承ListController在原来的基础上进⾏扩展
    var BiConListController = ListController.extend({
        renderButtons: function () {
            console.log('进⼊物料审批');
            this._super.apply(this, arguments);
            if (this.$buttons) {
                //这⾥找到刚才定义的class名为approval的按钮
                var btn = this.$buttons.find('.approval');
                var btn2 = this.$buttons.find('.refuse');
                //给按钮绑定click事件和⽅法to_pass、to_refuse
                btn.on('click', this.proxy('to_pass'));
                btn2.on('click', this.proxy('to_refuse'));
            }
        },


        to_pass: function () {
            var self = this;
            //这⾥是获取tree视图中选中的数据的记录集
            var records = _.map(self.selectedRecords, function (id) {
                return self.model.localData[id];
            });
            console.log("pass数据id：" + _.pluck(records, 'res_id'));
            //获取到数据集中每条数据的对应数据库id集合
            var ids = _.pluck(records, 'res_id');
            this._rpc({
                model: 'warehouse.approval',
                method: 'to_agree',
                args: [{"ids": ids}],
            }).then(function () {
                location.reload();
            });
        },

        to_refuse: function () {
            var self = this;
            //这⾥是获取tree视图中选中的数据的记录集
            var records = _.map(self.selectedRecords, function (id) {
                return self.model.localData[id];
            });
            console.log("refuse数据id：" + _.pluck(records, 'res_id'));
            //获取到数据集中每条数据的对应数据库id集合
            var ids = _.pluck(records, 'res_id');
            this._rpc({
                model: 'warehouse.approval',
                method: 'to_refuse',
                args: [{"ids": ids}],
            }).then(function () {
                location.reload();
            });
        },

    });
    //这块代码是继承ListView在原来的基础上进⾏扩展
    //这块⼀般只需要在config中添加上⾃⼰的Model,Renderer,Controller
    //这⾥我就对原来的Controller进⾏了扩展编写，所以就配置了⼀下BiConListController
    var BiConListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: BiConListController,
        }),
    });
    //这⾥⽤  来注册编写的视图BiConListView，第⼀个字符串是注册名到时候需要根据注册名调⽤视图
    viewRegistry.add('bicon_list_view_button_approval', BiConListView);
    return BiConListView;
});