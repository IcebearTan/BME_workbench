from datetime import datetime
from workbench.extensions import db
from sqlalchemy.orm import synonym
from flask import current_app

class UserModel(db.Model):
    __tablename__ = 'directory_user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    person_id = db.Column(db.Integer)
    avatar_url = db.Column(db.String(512))
    status = db.Column(db.String(20), default='active')
    lifecycle = db.Column(db.String(20), default='active')
    verification_status = db.Column(db.String(20), default='unverified')
    def is_admin(self):
        from workbench.models import Account, PermissionGrant
        account = Account.query.filter_by(issuer=current_app.config['IDENTITY_ISSUER'], subject=str(self.id)).first()
        return bool(account and not account.disabled and not account.person.blocked and
                    db.session.get(PermissionGrant, (account.id, 'governance:manage')))

class PersonWorkspaceRestrictionModel(db.Model):
    """人员级工作区否决：账号级 veto 随人员走——换主账号不得绕过（规格 9.4）。
    旧账号级 veto 有冲突按更严格结果处理并支持人工申诉（state=lifted 留痕）。"""
    __tablename__ = 'person_workspace_restriction'
    person_id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(20), nullable=False, server_default='vetoed')  # vetoed/lifted
    reason = db.Column(db.String(255), nullable=False)
    source_event = db.Column(db.String(64))
    version = db.Column(db.Integer, nullable=False, server_default='1')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

class ClubGroup(db.Model):
    """组别树节点。组名全树唯一（徽标只显组名不显路径的唯一性前提）；层级沿 parent_id 推导，
    应用层限深 ≤4；改名 id 键控零迁移；删除仅零引用，有引用走 archived（架构页隐藏、历史可解析）。"""
    __tablename__ = 'club_group'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('club_group.id'), nullable=True, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)     # 同父内排序，小在前
    status = db.Column(db.String(20), nullable=False, default='active', index=True)  # active / archived
    description = db.Column(db.Text)                                  # 小组介绍（组织页组态展示位，≤500 字）

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class ClubPosition(db.Model):
    """职位定义：规则字段全部可配（原硬编码 R1-R4 语义转字段）。
    org_slot 类别显式化（migrate_70）：club=社团职务（全社治理，社长/副社长/团支书类）/
    group=组内职位（组长类，每组各一）；空=按 sort_rank 兜底（services/club_rules.py 单源）。
    group_rule 挂组约束；per_group_limit 同组同时在任上限（0=不限）；global_limit 全社上限（0=不限）；
    sort_rank 排序+徽标优先级（小=高；列名避开 MySQL 保留字 rank）；badge_tier 徽标样式层；
    badge_with_group 徽标是否拼组段。"""
    __tablename__ = 'club_position'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False, unique=True)
    org_slot = db.Column(db.String(10))                             # club / group；空=按 sort_rank 派生
    sort_rank = db.Column(db.Integer, nullable=False, default=99)
    badge_tier = db.Column(db.Integer, nullable=False, default=3)     # 1 干事强调 / 2 组长次强调 / 3 组名中性
    badge_with_group = db.Column(db.Boolean, nullable=False, default=False)
    group_rule = db.Column(db.String(20), nullable=False, default='optional')  # forbidden / optional / required
    per_group_limit = db.Column(db.Integer, nullable=False, default=1)
    global_limit = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default='active', index=True)  # active / retired
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class ClubMembership(db.Model):
    """全员组归属（主要干活 primary ×1 + 帮忙 secondary ×0~1）。非治理事实：调整即覆盖更新，
    无卸任留痕；(user_id, slot) 唯一；同人两槽不同组、组须 active 在应用层校验。"""
    __tablename__ = 'club_membership'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('directory_user.id'), nullable=False, index=True)
    group_id = db.Column(db.Integer, db.ForeignKey('club_group.id'), nullable=False, index=True)
    slot = db.Column(db.String(20), nullable=False)                   # primary / secondary
    joined_at = db.Column(db.Date, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    __table_args__ = (db.UniqueConstraint('user_id', 'slot', name='uq_club_membership_user_slot'),)

class ClubOfficer(db.Model):
    """社团干事任职行。卸任 = status 置 ended 不删行（appointed_by/ended_by 操作人留痕）。
    title_id/group_id 为真相源（职位/组别解耦，校验读职位规则字段）；title/department 冗余存名
    双写过渡（旧 admin UI 与 e2e 兼容，Phase C admin 改版后退役删列）。
    约束（应用层，读 ClubPosition 配置）：挂组按 group_rule；同组/全社限额按 per_group_limit/
    global_limit；一人至多 1 条 active（原「兼两组」由 membership 两槽承接）。"""
    __tablename__ = 'club_officer'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('directory_user.id'), nullable=False, index=True)
    title_id = db.Column(db.Integer, db.ForeignKey('club_position.id'), nullable=True, index=True)
    group_id = db.Column(db.Integer, db.ForeignKey('club_group.id'), nullable=True, index=True)
    title = db.Column(db.String(30), nullable=False)              # 冗余：职位名（双写过渡）
    department = db.Column(db.String(50))                         # 冗余：组名（双写过渡；空=不挂组）
    term_start = db.Column(db.Date)
    term_end = db.Column(db.Date)                                 # 任期止（空 = 在任）
    status = db.Column(db.String(20), nullable=False, default='active', index=True)  # active / ended
    appointed_by = db.Column(db.Integer)                          # 任命操作人（审计留痕，非 FK）
    ended_by = db.Column(db.Integer)                              # 卸任操作人
    end_reason = db.Column(db.String(200))                        # 卸任原因（选填）
    scope_note = db.Column(db.String(200))                        # 任职范围描述（选填；个人主页社团身份卡展示）
    person_id = db.Column(db.Integer, index=True)
    org_slot_snapshot = db.Column(db.String(10))
    record_source = db.Column(db.String(20), nullable=False, default='legacy', server_default='legacy')
    source_note = db.Column(db.String(500))
    historical_year = db.Column(db.Integer)
    appointed_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class WorkWorkspace(db.Model):
    """组工作区：一个启用组别最多一个（club_group_id 唯一），只存协作配置，
    不复制组名/父组/成员名单（组织事实归 club_* 表，方案 §4.2）。"""
    __tablename__ = 'work_workspace'
    id = db.Column(db.Integer, primary_key=True)
    club_group_id = db.Column(db.Integer, db.ForeignKey('club_group.id'),
                              nullable=True, unique=True, index=True)
        # club 工作区（scope=club）为 NULL=社团级（跨组方案 §4.4，不新增组织节点）
    scope = db.Column(db.String(10), nullable=False, default='group')
        # group=组工作区 / club=社团工作区（X3）
    status = db.Column(db.String(20), nullable=False, default='active', index=True)
        # active / disabled（停用=入口只读关闸，数据与授权记录保留，D04）
    auto_grant = db.Column(db.Boolean, nullable=False, default=True)
        # 入职自动授（2026-10-01 授权自动化）：归属/任职写入即派生授权（provisioning.py）
    default_reviewer_user_id = db.Column(db.Integer)             # 默认验收人建议（选填）
    config_json = db.Column(db.Text)                             # 值班时段/提醒窗口/配额覆盖
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class WorkAccessGrant(db.Model):
    """协作授权（方案 §5.1）。资格（组织身份）≠授权：本表才是操作权限的真相源。
    有效性=每请求实时判定（services/work/access.py）：status/有效期 + 来源行仍匹配——
    officer 来源要求任职仍 active 且在任期内（到期即失效，不等定时卸任）；
    membership 来源要求归属行仍在授权时快照的组（A06 防原地改组带权漂移）。
    岗位模板仅三值，不做任意权限表达式。"""
    __tablename__ = 'work_access_grant'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
        # member（本组工作人员）/ coordinator（本组协调员）/ governance（授权治理，全局）
    workspace_id = db.Column(db.Integer, db.ForeignKey('work_workspace.id'),
                             nullable=True, index=True)          # governance 授权为 NULL=全局
    source_type = db.Column(db.String(20), nullable=False)       # officer / membership / direct
    source_id = db.Column(db.Integer, nullable=True)             # officer_id 或 membership_id；direct 为空
    group_id_snapshot = db.Column(db.Integer, nullable=True)     # membership 来源必填：授权时组快照
    valid_from = db.Column(db.Date, nullable=True)               # 空=即时生效
    valid_until = db.Column(db.Date, nullable=True)              # 空=不限期（覆盖任期判断）
    status = db.Column(db.String(20), nullable=False, default='active', index=True)
        # active / revoked / vetoed（vetoed=治理否决：本 (user, workspace) 不再自动重授）
    subtree = db.Column(db.Boolean, nullable=False, default=False)
        # 子树汇总（跨组方案 §4.1）：coordinator 授权勾选后，额外可见本组子孙组
        # 工作区事项的「摘要」（标题/负责人/状态/截止，无正文）；正文仍走参与/邀请
    origin = db.Column(db.String(10), nullable=False, default='manual')
        # auto=随组织事实派生（provisioning.py）/ manual=治理手动开通
    revoke_reason = db.Column(db.String(200))
    granted_by = db.Column(db.Integer, nullable=False)           # 操作人留痕（非 FK）
    grant_reason = db.Column(db.String(200), nullable=False)     # 授权原因（方案 §5.4 必填）
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    __table_args__ = (
        db.Index('ix_work_access_grant_ws_role', 'workspace_id', 'role'),
    )

class WorkItem(db.Model):
    """工作事项（话题与任务同构，方案 §7/§8）：kind 区分合法状态集——
    topic: draft/open/closed；task: draft/todo/in_progress/blocked/review/done/cancelled。
    话题转任务保留原 ID 与讨论（promote 同事务切换 kind/status，B04）。"""
    __tablename__ = 'work_item'
    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('work_workspace.id'),
                             nullable=False, index=True)
    kind = db.Column(db.String(10), nullable=False)              # topic / task
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text)                                    # markdown（服务端 nh3 清洗后存储）
    visibility = db.Column(db.String(20), nullable=False, default='workspace', index=True)
        # workspace（本工作区可见）/ participants（仅指定参与人，协调员无天然阅读权）
    status = db.Column(db.String(20), nullable=False, default='draft', index=True)
    created_by = db.Column(db.Integer, nullable=False, index=True)
    version = db.Column(db.Integer, nullable=False, default=1)   # 乐观锁（expected_version）
    idempotency_key = db.Column(db.String(64), nullable=True)    # 创建幂等键
    promoted_at = db.Column(db.DateTime, nullable=True)          # 话题转任务时刻
    closed_reason = db.Column(db.String(200))
    last_reply_seq = db.Column(db.Integer, nullable=False, default=0)  # 回复序号水位
    last_activity_at = db.Column(db.DateTime, default=datetime.now, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    __table_args__ = (
        # 幂等键按创建者隔离（B01：跨用户撞 key 不互相干扰，也不能占位他人 key 致 500）
        db.UniqueConstraint('created_by', 'idempotency_key', name='uq_work_item_idem'),
        db.Index('ix_work_item_ws_kind_status', 'workspace_id', 'kind', 'status'),
    )

class WorkItemParticipant(db.Model):
    """事项参与关系（协作者/观察者）。参与关系不越过有效协作资格（邀请时校验）；
    同一用户不重复激活：重邀原地复活（removed_at 置空，ClubMembership 覆盖先例）。"""
    __tablename__ = 'work_item_participant'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('work_item.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    ptype = db.Column(db.String(20), nullable=False, default='collaborator')
        # collaborator / reviewer / observer
    invited_by = db.Column(db.Integer, nullable=True)
    joined_at = db.Column(db.DateTime, default=datetime.now)
    removed_at = db.Column(db.DateTime, nullable=True)
    __table_args__ = (
        db.UniqueConstraint('item_id', 'user_id', name='uq_work_item_participant_item_user'),
    )

class WorkTask(db.Model):
    """任务属性（与 work_item 一对一）。负责人唯一；草稿允许缺负责人/时限，
    发布前必须补齐（应用层）。due_at 为逾期计算源（逾期≠状态，方案 §8.2）。"""
    __tablename__ = 'work_task'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('work_item.id'), nullable=False, unique=True)
    assignee_user_id = db.Column(db.Integer, nullable=True, index=True)
    reviewer_user_id = db.Column(db.Integer, nullable=True, index=True)   # 指定验收人（选填）
    start_at = db.Column(db.DateTime, nullable=True)
    due_at = db.Column(db.DateTime, nullable=True, index=True)
    priority = db.Column(db.String(20), nullable=False, default='normal')  # normal / high / urgent
    accept_criteria = db.Column(db.Text)                         # 验收标准
    published_at = db.Column(db.DateTime, nullable=True)
    last_accepted_submission_id = db.Column(db.Integer, nullable=True)    # 冗余：最近通过提交
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class WorkReply(db.Model):
    """事项回复（单层时间线，可引用同事项另一条）。撤回=removed_at 置位留占位
    不回正文；编辑走 work_reply_revision 留修订史（超窗只能追加更正）。
    client_request_id 按发送者幂等（B01：网络重试不生成重复回复）。"""
    __tablename__ = 'work_reply'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('work_item.id'), nullable=False, index=True)
    seq = db.Column(db.Integer, nullable=False)                  # 事项内单调递增（服务器分配）
    author_id = db.Column(db.Integer, nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)                    # 纯文本（首期）
    reply_to_id = db.Column(db.Integer, db.ForeignKey('work_reply.id'), nullable=True)
    client_request_id = db.Column(db.String(64), nullable=False)
    edited_at = db.Column(db.DateTime, nullable=True)
    removed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    __table_args__ = (
        db.UniqueConstraint('item_id', 'seq', name='uq_work_reply_item_seq'),
        db.UniqueConstraint('author_id', 'client_request_id', name='uq_work_reply_author_request'),
    )

class WorkReplyRevision(db.Model):
    """回复修订史：编辑窗口内的历史版本全量留存，正文列只存当前值。
    首期契约：回复编辑 UI 与对应端点推迟（设计 §7.4 已记录该裁剪），本表为
    预留结构，暂无写入方；接入编辑端点时由服务层在此留修订行。"""
    __tablename__ = 'work_reply_revision'
    id = db.Column(db.Integer, primary_key=True)
    reply_id = db.Column(db.Integer, db.ForeignKey('work_reply.id'), nullable=False, index=True)
    seq = db.Column(db.Integer, nullable=False)                  # 同回复内递增
    body = db.Column(db.Text, nullable=False)                    # 修订前正文
    edited_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    __table_args__ = (
        db.UniqueConstraint('reply_id', 'seq', name='uq_work_reply_revision_reply_seq'),
    )

class WorkResponseRequest(db.Model):
    """待回应请求（方案 §7.2）：明确要求某人回应时才建，已读≠回应。
    创建/回复同事务维护状态。"""
    __tablename__ = 'work_response_request'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('work_item.id'), nullable=False, index=True)
    reply_id = db.Column(db.Integer, nullable=True)              # 挂在某条回复上（选填）
    responder_user_id = db.Column(db.Integer, nullable=False, index=True)
    due_at = db.Column(db.DateTime, nullable=True)               # 建议回复时限
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
        # pending / responded / declined / expired / cancelled
    response_reply_id = db.Column(db.Integer, nullable=True)     # 回应回复（responded 时）
    created_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    responded_at = db.Column(db.DateTime, nullable=True)

class WorkTransferRequest(db.Model):
    """负责人转交请求（方案 §8.4）：目标明确接手后才替换负责人；
    「同事项仅一个待确认」由应用层 FOR UPDATE 锁事项行保证（MySQL 无部分唯一索引）。"""
    __tablename__ = 'work_transfer_request'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('work_item.id'), nullable=False, index=True)
    from_user_id = db.Column(db.Integer, nullable=False)
    to_user_id = db.Column(db.Integer, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
        # pending / accepted / rejected / withdrawn / expired
    reason = db.Column(db.String(200))
    expires_at = db.Column(db.DateTime, nullable=False)
    item_version = db.Column(db.Integer, nullable=False)         # 发起时事项版本（过期判定参考）
    decided_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class WorkHandoff(db.Model):
    """跨组交付（跨组方案 §4.2，migrate_59）：组对组的显式交接，事项所有权不动。
    发起=源事项协调员∨作者（kind 为用途自由填写，不承担流程语义）；目标组协调员
    接单后同事务在本组工作区生成关联任务，任务完成时回填源事项。交付包（说明+
    固定版本文件）对接单组只读，源事项正文不自动放开（与 §9.5 授权转交同构）。"""
    __tablename__ = 'work_handoff'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('work_item.id'), nullable=False, index=True)
    from_workspace_id = db.Column(db.Integer, db.ForeignKey('work_workspace.id'),
                                  nullable=False, index=True)
    to_workspace_id = db.Column(db.Integer, db.ForeignKey('work_workspace.id'),
                                nullable=False, index=True)
    kind = db.Column(db.String(30), nullable=False)              # 用途：自由填写 ≤30 字（UI 给快捷建议）
    note = db.Column(db.Text)                                    # 交付说明（给目标组的上下文）
    deadline = db.Column(db.DateTime, nullable=True)             # 期望完成时间
    status = db.Column(db.String(20), nullable=False, default='offered', index=True)
        # offered / accepted / declined / withdrawn / expired / done
    accepted_item_id = db.Column(db.Integer, nullable=True)      # 接单时在目标组生成的关联任务
    result_note = db.Column(db.Text)                             # 目标组回填的执行结果
    created_by = db.Column(db.Integer, nullable=False)
    decided_by = db.Column(db.Integer, nullable=True)
    decided_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    __table_args__ = (
        # 在途唯一（offered 态）由应用层校验 + 源事项行锁串行化保证；
        # 不建数据库唯一索引——终态（done/declined/expired）后允许同用途再发起
        db.Index('ix_work_handoff_item_to_kind', 'item_id', 'to_workspace_id', 'kind'),
    )

class WorkSubmission(db.Model):
    """任务交付提交：每次提交不可覆盖；验收决策绑定具体提交行（B05——交付文件
    经 work_file_link(purpose=submission_result) 固定版本，验收后内容不可被悄悄替换）。"""
    __tablename__ = 'work_submission'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('work_item.id'), nullable=False, index=True)
    seq = db.Column(db.Integer, nullable=False)
    submitted_by = db.Column(db.Integer, nullable=False)
    result_note = db.Column(db.Text)                             # 结果说明
    decision = db.Column(db.String(20), nullable=True)           # accepted / returned（空=待验收）
    decided_by = db.Column(db.Integer, nullable=True)
    decided_at = db.Column(db.DateTime, nullable=True)
    decision_note = db.Column(db.Text)                           # 退回原因（退回必填）
    created_at = db.Column(db.DateTime, default=datetime.now)
    __table_args__ = (
        db.UniqueConstraint('item_id', 'seq', name='uq_work_submission_item_seq'),
    )

class WorkEvent(db.Model):
    """工作时间线（方案 §10.1）：不可变追加记录，与业务变更同事务落库；
    对话可修订、事件只追加。actor_snapshot 存操作时职位/组快照（换届后仍可解释
    「当时为什么有权」）。"""
    __tablename__ = 'work_event'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('work_item.id'), nullable=False, index=True)
    seq = db.Column(db.Integer, nullable=False)                  # 事项内事件序号唯一
    actor_user_id = db.Column(db.Integer, nullable=True)         # 空=系统后台动作
    actor_snapshot = db.Column(db.String(200), nullable=True)    # 操作时身份快照（职位·组）
    event_type = db.Column(db.String(30), nullable=False)
        # created/published/edited/replied/closed/reopened/promoted/assigned/transfer_requested/
        # transfer_accepted/status_changed/due_changed/priority_changed/submitted/reviewed/
        # participant_added/participant_removed/file_attached/visibility_changed/emergency_access
    diff_json = db.Column(db.Text)                               # 前后差异（最小字段）
    reason = db.Column(db.String(200))
    request_id = db.Column(db.String(64))                        # 幂等/追踪
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    __table_args__ = (
        db.UniqueConstraint('item_id', 'seq', name='uq_work_event_item_seq'),
    )

class WorkReadState(db.Model):
    """已读游标（按人×事项）：只进不退，服务端校验不得越过本人可见最大 seq。"""
    __tablename__ = 'work_read_state'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('work_item.id'), nullable=False, index=True)
    last_read_seq = db.Column(db.Integer, nullable=False, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'item_id', name='uq_work_read_state_user_item'),
    )

class WorkFile(db.Model):
    """私有工作文件（逻辑文件）：属于事项（首期必挂事项，方案 §9.1），非个人网盘；
    本体在 storage 私有命名空间（work/ 前缀不经 /media 公开链路）。"""
    __tablename__ = 'work_file'
    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('work_workspace.id'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('work_item.id'), nullable=False, index=True)
    display_name = db.Column(db.String(200), nullable=False)     # 显示名（存储键服务端生成）
    status = db.Column(db.String(20), nullable=False, default='uploading', index=True)
        # uploading / active / quarantined / removed
    current_version_id = db.Column(db.Integer, nullable=True)    # 裸引用避免与版本表循环 FK
    created_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class WorkFileVersion(db.Model):
    """文件版本（不可变）：上传新版本生成新行不覆盖旧文件；格式校验与病毒扫描
    状态分开保存（首期未启用扫描=not_required，状态位先行，方案 §9.2）。"""
    __tablename__ = 'work_file_version'
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('work_file.id'), nullable=False, index=True)
    version_no = db.Column(db.Integer, nullable=False)           # 同文件内递增
    object_key = db.Column(db.String(300), nullable=False)       # work/files/{item}/{file}/v{n}_{uuid}{ext}
    size = db.Column(db.Integer, nullable=False, default=0)
    content_type = db.Column(db.String(100))
    checksum_sha256 = db.Column(db.String(64), nullable=True)
    format_check = db.Column(db.String(20), nullable=False, default='pending')
        # pending / passed / failed（扩展名∩魔数∩声明类型交叉）
    scan_status = db.Column(db.String(20), nullable=False, default='not_required')
        # not_required / pending / passed / failed
    detect_rules_version = db.Column(db.String(20), nullable=True)
    uploaded_by = db.Column(db.Integer, nullable=False)
    prev_version_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    __table_args__ = (
        db.UniqueConstraint('object_key', name='uq_work_file_version_key'),
        db.UniqueConstraint('file_id', 'version_no', name='uq_work_file_version_file_no'),
    )

class WorkFileLink(db.Model):
    """文件引用（显式外键，方案 §9.5）：附件归属事项；交付固定版本（submission
    用途 version_id 必填）。下载按「本次关联」判权，不因上传者是本人放行。"""
    __tablename__ = 'work_file_link'
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('work_file.id'), nullable=False, index=True)
    version_id = db.Column(db.Integer, nullable=True)            # NULL=跟随最新；submission 用途必填
    target_type = db.Column(db.String(20), nullable=False)       # item / submission（白名单）
    target_id = db.Column(db.Integer, nullable=False)
    purpose = db.Column(db.String(20), nullable=False, default='attachment')
        # attachment / submission_result
    shared_from_link_id = db.Column(db.Integer, nullable=True)   # 授权转交来源（后续阶段）
    created_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class WorkNotificationReceipt(db.Model):
    """工作通知回执：事件×接收人×类型数据库去重（超时重试不产生重复提醒，
    方案 §10.2）。与业务变更同事务写入。"""
    __tablename__ = 'work_notification_receipt'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, nullable=False, index=True)  # 裸引用（与事件同事务）
    user_id = db.Column(db.Integer, nullable=False)
    notify_type = db.Column(db.String(30), nullable=False)
        # reply_to_me/response_requested/mentioned/assigned/transfer_pending/review_requested/
        # status_changed/due_soon/overdue/follow_up
    notification_id = db.Column(db.Integer, nullable=True)        # 生成的通知行
    created_at = db.Column(db.DateTime, default=datetime.now)
    __table_args__ = (
        db.UniqueConstraint('event_id', 'user_id', 'notify_type',
                            name='uq_work_notification_receipt_dedupe'),
    )

class WorkReminder(db.Model):
    """持久提醒（方案 §10.3）：任务改期/完成/换人时旧提醒按版本自然失效
    （regenerate 取消旧 pending 后按新版本写入）；扫描器原子认领、重启可恢复。
    object_version 语义随 slot：due_soon/overdue/follow_up=事项 version；
    response_due=回应请求 id。"""
    __tablename__ = 'work_reminder'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('work_item.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=False)
    slot = db.Column(db.String(20), nullable=False)
        # due_soon / overdue / follow_up / response_due
    object_version = db.Column(db.Integer, nullable=False)
    trigger_at = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
        # pending / claimed / sent / failed / cancelled
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    next_retry_at = db.Column(db.DateTime, nullable=True)
    claimed_at = db.Column(db.DateTime, nullable=True)           # 认领超时回收依据（C04）
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    __table_args__ = (
        db.UniqueConstraint('item_id', 'user_id', 'slot', 'object_version',
                            name='uq_work_reminder_dedupe'),
    )

class ClubOrgEvent(db.Model):
    """组织变更事件（方案 §3.3/§17.1）：ClubMembership 原地覆盖无历史，本表补
    变更留痕，供授权解释与交接还原。由 club_admin/officers 集中挂钩写入（同事务）。"""
    __tablename__ = 'club_org_event'
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(30), nullable=False, index=True)
        # membership_set / membership_batch / group_archived / officer_appointed /
        # officer_edited / officer_ended
    user_id = db.Column(db.Integer, nullable=True, index=True)
    membership_id = db.Column(db.Integer, nullable=True)
    officer_id = db.Column(db.Integer, nullable=True)
    from_group_id = db.Column(db.Integer, nullable=True)
    to_group_id = db.Column(db.Integer, nullable=True)
    operator_id = db.Column(db.Integer, nullable=True)
    detail_json = db.Column(db.Text)
    occurred_at = db.Column(db.DateTime, default=datetime.now, index=True)

class WorkObjectClaim(db.Model):
    """对象认领（跨组方案 §4.3 通用化，X2）：工作区对任意可关联对象的「维护
    责任」登记——组织约定的登记，不是权限（读原对象仍按其业务模块规则）。
    仅投影适配器 stewardable=True 的类型可认领（首期=课程；流程性对象关闭）。"""
    __tablename__ = 'work_object_claim'
    id = db.Column(db.Integer, primary_key=True)
    source_type = db.Column(db.String(30), nullable=False, index=True)
    source_id = db.Column(db.Integer, nullable=False, index=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('work_workspace.id'),
                             nullable=False, index=True)
    claimed_by = db.Column(db.Integer, nullable=False)
    claimed_at = db.Column(db.DateTime, default=datetime.now)
    __table_args__ = (
        db.UniqueConstraint('source_type', 'source_id', 'workspace_id',
                            name='uq_work_object_claim'),
    )

class WorkBusinessLink(db.Model):
    """业务关联（方案 §11.3）：只读投影，关联不授予原业务权限、完成不自动改变
    原业务。source_type 白名单（course/camp_session/feedback_ticket），服务层验证
    目标存在与访问权，不接受任意表名。"""
    __tablename__ = 'work_business_link'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('work_item.id'), nullable=False, index=True)
    source_type = db.Column(db.String(30), nullable=False)
    source_id = db.Column(db.Integer, nullable=False)
    relation = db.Column(db.String(20), nullable=False, default='related')
    created_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    __table_args__ = (
        db.UniqueConstraint('item_id', 'source_type', 'source_id',
                            name='uq_work_business_link_unique'),
    )
