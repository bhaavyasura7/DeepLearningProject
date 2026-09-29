import '../styles/globals.css';
import Head from 'next/head';

export default function MyApp({ Component, pageProps }) {
  return (
    <>
      <Head>
        <title>AuraRec — Proactive AI Movie Recommender</title>
        <meta name="description" content="Agentic AI-based proactive movie recommendation system using dynamic user preference memory" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </Head>
      <Component {...pageProps} />
    </>
  );
}
