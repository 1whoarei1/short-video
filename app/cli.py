"""Codex file-bridge commands. Waiting observes local files; it cannot wake idle Codex."""
import argparse
import json
import math
import sys
import time
from pathlib import Path
from .workflow import Workflow, LEGACY_STAGES, MODES


def wait_for_request(flow, timeout=300, after_revision=None, interval=.5):
    if not math.isfinite(timeout) or not 0 <= timeout <= 3600:
        raise ValueError('等待时间必须在 0–3600 秒之间')
    deadline = time.monotonic() + timeout
    while True:
        state = flow.read()
        request = state.get('taskRequest')
        action = state['nextAction']
        if request and request['status'] == 'queued' and action['actor'] == 'agent':
            return {'event': 'request', 'project': state, 'message': '已收到本地继续请求；请领取并执行，直到当前模式确认点'}
        if request and request['status'] == 'cancelled':
            return {'event': 'cancelled', 'project': state, 'message': '用户已暂停继续请求，请停止新的制作操作'}
        if after_revision is not None and state['revision'] != after_revision:
            return {'event': 'changed', 'project': state, 'message': '项目已改变；重新检查 nextAction 后决定继续或等待'}
        if action['action'] == 'complete':
            return {'event': 'complete', 'project': state, 'message': '项目已完成'}
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {'event': 'timeout', 'project': state, 'message': '等待已超时，未启动任何生成。网页只能保存请求，不能唤醒空闲 Codex；回到 Codex 继续对话，或在仍活跃的任务中再次运行 wait。'}
        time.sleep(min(interval, remaining))


def main(argv=None):
    parser = argparse.ArgumentParser(description='视频工作台项目操作（本地文件桥接，无模型 API）')
    parser.add_argument('--workspace', default='workspace')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    command = sub.add_parser('wait', help='活跃 Codex 有界等待网页请求；不会唤醒空闲对话')
    command.add_argument('--timeout', type=float, default=300)
    command.add_argument('--after-revision', type=int)
    command = sub.add_parser('save')
    command.add_argument('--stage', choices=LEGACY_STAGES, required=True)
    command.add_argument('--file', required=True)
    command.add_argument('--settings', help='可选需求配置 JSON 文件')
    command = sub.add_parser('artifact')
    command.add_argument('--stage', choices=LEGACY_STAGES, required=True)
    command.add_argument('--path', required=True)
    command.add_argument('--label', default='')
    command.add_argument('--role', default='')
    for name in ('submit', 'approve', 'revise'):
        command = sub.add_parser(name)
        command.add_argument('--stage', choices=LEGACY_STAGES, required=True)
        if name in ('submit', 'approve'):
            command.add_argument('--by', choices=['agent', 'human'], default='agent')
        if name == 'approve':
            command.add_argument('--note', default='')
    command = sub.add_parser('mode')
    command.add_argument('--workflow-mode', choices=MODES)
    command.add_argument('--self-review', choices=['on', 'off'])
    sub.add_parser('request', help='显式保存继续请求；只允许已通过人工确认点的项目')
    command = sub.add_parser('claim')
    command.add_argument('--id', required=True)
    command = sub.add_parser('release', help='执行受阻时释放任务并写明原因')
    command.add_argument('--id', required=True)
    command.add_argument('--note', required=True)
    command = sub.add_parser('cancel', help='暂停继续请求；不声称终止外部渲染进程')
    command.add_argument('--id', required=True)
    sub.add_parser('undo')
    command = sub.add_parser('resolve')
    command.add_argument('--id', required=True)
    command.add_argument('--resolved', choices=['yes', 'no'], default='yes')
    for name, command in sub.choices.items():
        if name in ('save', 'artifact', 'submit', 'approve', 'revise', 'resolve'):
            command.add_argument('--task-id', dest='taskId')
            command.add_argument('--revision', type=int)
            if name not in ('submit', 'approve'):
                command.add_argument('--by', choices=['agent', 'human'], default='agent')
    for name in ('claim', 'cancel', 'release'):
        sub.choices[name].add_argument('--revision', type=int)
    args = parser.parse_args(argv)
    try:
        flow = Workflow(args.workspace)
        if args.command == 'status':
            result = flow.read()
        elif args.command == 'wait':
            result = wait_for_request(flow, args.timeout, args.after_revision)
        else:
            data = {key: value for key, value in vars(args).items() if value is not None}
            if args.command == 'save':
                data['text'] = Path(args.file).read_text(encoding='utf-8')
                if args.settings:
                    data['settings'] = json.loads(Path(args.settings).read_text(encoding='utf-8'))
                else:
                    data.pop('settings', None)
            if args.command == 'resolve':
                data['resolved'] = args.resolved == 'yes'
            if args.command == 'mode':
                if args.workflow_mode is not None:
                    data['workflowMode'] = args.workflow_mode
                if args.self_review is not None:
                    data['selfReview'] = args.self_review == 'on'
            if args.command == 'request':
                data['by'] = 'agent'
            result = flow.mutate(args.command, data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
