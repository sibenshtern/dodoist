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
          title: 'Documentation',
          items: [
            { label: 'Overview',        to: '/docs/intro' },
            { label: 'Technologies',    to: '/docs/technologies' },
            { label: 'Architecture',    to: '/docs/architecture' },
            { label: 'Database schema', to: '/docs/database' },
            { label: 'API reference',   to: '/docs/api-documentation' },
            { label: 'Deployment',      to: '/docs/deployment' },
          ],
        },
        {
          title: 'ADR',
          items: [
            { label: 'User',    to: '/docs/ADR/user' },
            { label: 'Project', to: '/docs/ADR/project' },
            { label: 'Task',    to: '/docs/ADR/task' },
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
  } satisfies Preset.ThemeConfig,
};

export default config;
