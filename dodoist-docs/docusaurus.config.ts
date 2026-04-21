import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Dodoist',
  tagline: 'Personal tasks and project management — in one place.',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  markdown: {
    format: 'detect',
  },

  url: 'https://dodoist.sibenshtern.ru',
  baseUrl: '/',

  organizationName: 'sibenshtern',
  projectName: 'dodoist',

  onBrokenLinks: 'throw',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  plugins: ['docusaurus-plugin-image-zoom'],

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: undefined,
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/docusaurus-social-card.jpg',
    colorMode: {
      defaultMode: 'light',
      respectPrefersColorScheme: false,
    },
    navbar: {
      title: 'Dodoist',
      logo: {
        alt: 'Dodoist',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'tutorialSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          href: 'https://github.com/sibenshtern/dodoist',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Документация',
          items: [
            { label: 'Обзор',           to: '/docs/intro' },
            { label: 'Технологии',      to: '/docs/technologies' },
            { label: 'Архитектура',     to: '/docs/architecture' },
            { label: 'База данных',     to: '/docs/database' },
            { label: 'Деплой',          to: '/docs/deployment' },
          ],
        },
        {
          title: 'API',
          items: [
            { label: 'Проекты',  to: '/docs/ADR/projects' },
            { label: 'Задачи',   to: '/docs/ADR/tasks' },
          ],
        },
        {
          title: 'Архитектурные решения',
          items: [
            { label: 'ADR-001: WIP-лимит',      to: '/docs/ADR/adr-001-wip-limit-enforcement' },
            { label: 'ADR-002: Django Admin',   to: '/docs/ADR/adr-002-django-admin' },
            { label: 'ADR-003: Typeahead',      to: '/docs/ADR/adr-003-parent-task-typeahead' },
            { label: 'ADR-004: Уведомления',    to: '/docs/ADR/adr-004-notification-pipeline' },
          ],
        },
        {
          title: 'История изменений',
          items: [
            { label: 'Phase 0 — Стабилизация', to: '/docs/changelog/phase-0' },
          ],
        },
      ],
      copyright: `© ${new Date().getFullYear()} Dodoist`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'json', 'sql', 'http'],
    },
    zoom: {
      selector: '.markdown img',
      background: {
        light: 'rgb(255, 255, 255)',
        dark: 'rgb(50, 50, 50)',
      },
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
