import { Component, signal } from '@angular/core';
import { NgClass } from '@angular/common';
import { RouterLink } from '@angular/router';

interface Task {
  text: string;
  badge: string | null;
  badgeClass: string | null;
  done: boolean;
}

interface PricingPlan {
  name: string;
  price: string;
  period: string;
  description: string;
  cta: string;
  highlighted: boolean;
  features: string[];
}

@Component({
  selector: 'app-landing',
  imports: [RouterLink, NgClass],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss',
})
export class LandingComponent {
  readonly featureBar = [
    {
      icon: '📥',
      title: 'Unified Inbox',
      description: 'Personal todos and work tasks in one view. Zero context switching.',
    },
    {
      icon: '🗂',
      title: 'Scrum & Kanban',
      description: 'Sprint planning, story points, boards — the full agile toolkit.',
    },
    {
      icon: '📈',
      title: 'Analytics',
      description: 'Burndown charts, velocity tracking, and individual performance metrics.',
    },
    {
      icon: '🔐',
      title: 'Role-based Access',
      description: 'Fine-grained permissions from System Admin to Guest — per project.',
    },
  ];

  readonly featureDetails = [
    {
      eyebrow: 'Personal + Work',
      heading: 'One inbox to rule them all',
      description:
        'Stop juggling between apps. Dodoist pulls your personal todos and Jira-style work tasks into a single, prioritized view — so you always know what to focus on next.',
      bullets: [
        'Smart daily digest with AI-ranked priorities',
        'Drag tasks between personal and work projects',
        'Recurring tasks with flexible schedules',
        'Calendar sync with Google & Outlook',
      ],
      visual: { icon: '📥', color: '#fff0ef', label: 'Unified Inbox' },
    },
    {
      eyebrow: 'Agile workflows',
      heading: 'Full Scrum & Kanban out of the box',
      description:
        'Everything your dev team needs — sprints, story points, swimlanes, epics — without the Jira complexity. Set up a board in seconds, not hours.',
      bullets: [
        'Sprint planning with drag-and-drop',
        'Story points & velocity tracking',
        'Custom fields per project type',
        'GitHub & GitLab PR linking',
      ],
      visual: { icon: '🗂', color: '#ebf2fd', label: 'Kanban Board' },
    },
    {
      eyebrow: 'Insights',
      heading: 'Analytics that actually help',
      description:
        'Burndown charts, individual velocity, blockers heatmaps — Dodoist surfaces the data that makes your retrospectives productive and your estimates accurate.',
      bullets: [
        'Burndown & burnup charts per sprint',
        'Individual & team velocity dashboards',
        'Blocker detection and alerts',
        'Export to CSV or share a live link',
      ],
      visual: { icon: '📈', color: '#f0fdf4', label: 'Analytics' },
    },
  ];

  readonly steps = [
    {
      number: '01',
      title: 'Create a workspace',
      description:
        'Set up your team workspace or keep it personal. Invite teammates with role-based permissions.',
    },
    {
      number: '02',
      title: 'Add your projects',
      description:
        'Choose Scrum, Kanban, or personal project type. Create tasks, sprints, and boards in seconds.',
    },
    {
      number: '03',
      title: 'Ship & measure',
      description:
        'Track velocity, monitor burndowns, and analyze individual performance with built-in analytics.',
    },
  ];

  readonly pricingPlans: PricingPlan[] = [
    {
      name: 'Free',
      price: '$0',
      period: 'forever',
      description: 'Perfect for individuals and small side projects.',
      cta: 'Get started free',
      highlighted: false,
      features: [
        'Up to 5 projects',
        'Unlimited personal tasks',
        'Kanban boards',
        'Basic analytics',
        '1 workspace',
      ],
    },
    {
      name: 'Pro',
      price: '$8',
      period: 'per month',
      description: 'For power users who need unlimited everything.',
      cta: 'Start free trial',
      highlighted: true,
      features: [
        'Unlimited projects',
        'Scrum + Kanban + Calendar',
        'Advanced analytics & reports',
        'GitHub & GitLab integration',
        'Priority support',
        'Custom fields',
      ],
    },
    {
      name: 'Team',
      price: '$16',
      period: 'per user / month',
      description: 'For teams shipping together with full agile workflows.',
      cta: 'Contact sales',
      highlighted: false,
      features: [
        'Everything in Pro',
        'Unlimited team members',
        'Role-based access control',
        'SSO & SAML',
        'Audit logs',
        'Dedicated support',
        'SLA guarantee',
      ],
    },
  ];

  tasks = signal<Task[]>([
    { text: 'Implement OAuth login flow', badge: 'Critical', badgeClass: 'badge--critical', done: false },
    { text: 'Review pull request #142', badge: 'High', badgeClass: 'badge--high', done: false },
    { text: 'Stand-up call with team', badge: null, badgeClass: null, done: true },
    { text: 'Buy groceries 🛒', badge: 'Personal', badgeClass: 'badge--personal', done: false },
    { text: 'Morning workout', badge: null, badgeClass: null, done: true },
  ]);

  toggleTask(index: number): void {
    this.tasks.update(list =>
      list.map((task, i) => (i === index ? { ...task, done: !task.done } : task))
    );
  }

  get doneCount(): number {
    return this.tasks().filter(t => t.done).length;
  }
}
