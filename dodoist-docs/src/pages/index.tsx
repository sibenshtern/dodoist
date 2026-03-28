import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';

import styles from './index.module.css';

const features = [
  {
    icon: '✓',
    iconBg: 'rgba(219, 64, 53, 0.10)',
    title: 'Личные и командные задачи',
    desc: 'Личный список дел и командные проекты в одном аккаунте. Не нужно переключаться между Todoist и Jira.',
  },
  {
    icon: '◈',
    iconBg: 'rgba(36, 111, 224, 0.10)',
    title: 'Kanban и Scrum',
    desc: 'Спринты для инженерных команд или непрерывный канбан для текущей работы. Виды: доска, список, календарь.',
  },
  {
    icon: '▲',
    iconBg: 'rgba(21, 128, 61, 0.10)',
    title: 'Встроенная аналитика',
    desc: 'Burndown-диаграммы, velocity, метрики по пользователям. Всё из коробки, без сторонних плагинов.',
  },
];

function Hero() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={styles.hero}>
      <div className="container">
        <div className={styles.heroPretitle}>
          <span>Документация</span>
        </div>
        <h1 className={styles.heroTitle}>{siteConfig.title}</h1>
        <p className={styles.heroSubtitle}>{siteConfig.tagline}</p>
        <div className={styles.heroCta}>
          <Link className="btn--hero-primary" to="/docs/intro">
            Начать читать
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M2.5 7h9M8 3.5 11.5 7 8 10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </Link>
          <Link className="btn--hero-outline" to="/docs/architecture">
            Архитектура
          </Link>
        </div>
      </div>
    </header>
  );
}

function Features() {
  return (
    <section className="features-section">
      <div className="container">
        <div className="row">
          {features.map((f) => (
            <div key={f.title} className="col col--4">
              <div className="feature-card">
                <div
                  className="feature-card__icon"
                  style={{background: f.iconBg, fontSize: 20}}
                >
                  {f.icon}
                </div>
                <p className="feature-card__title">{f.title}</p>
                <p className="feature-card__desc">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout title={siteConfig.title} description={siteConfig.tagline}>
      <Hero />
      <main>
        <Features />
      </main>
    </Layout>
  );
}
