功能要求：

1、物料编码随机生成，格式为（SZPDC）+随机数字

2、当审批状态为入库时，需要输入归还数量，并且物料管理中物料数量相对变化

3、当开关为TRUE,出库需要匹配序列号方能出库

4、申请数量不能高于仓库最大数量

5、审批状态为出库时，不可再修改表单

6、归还数量不可高于申请数量

7、审批按钮颜色为蓝色，tree视图

8、出库时，序列号与物料表中的序列号不符时，弹出提示信息

9、物料管理表以物料名称为分类，库存数量为柱形，可以使用odoo原视图代码展示该表单

10、菜单规划：仓库分类、物料管理、物料审批、物料归还，部门表

11、权限配置：

            仓库管理员：拥有自己仓库下的所有权限

            普通用户：能查看自己物料表单

            部门管理员：能查看自己部门的审批表单，上级部门拥有查看下级部门的审批