/* eslint-disable import/extensions */
import { defineNuxtConfig } from 'nuxt/config'
import createSitemapRoutes from './utils/createSitemap'

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  head: {
    title: 'test',
    htmlAttr: {
      lang: 'en',
    },
    meta: [
      { charset: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { hid: 'description', name: 'description', content: '' },
      { name: 'format-detection', content: 'telephone=no' },
    ],
    link: [{ rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }],
  },
  target: 'server',
  devtools: { enabled: true },
  css: ['~/assets/css/main.css'],
  postcss: {
    plugins: {
      tailwindcss: {},
      autoprefixer: {},
    },
  },
  modules: [
    '@nuxtjs/eslint-module',
    // 'nuxt-i18n',
    // '@nuxtjs/axios',
    // '@nuxtjs/auth-next',
    '@nuxt/image',
    // '@nuxtjs/toast',
  ],
  buildModules: ['@nuxtjs/tailwindcss'],
  sitemap: {
    hostname: process.env.WEB_URL,
    gzip: true,
    routes: createSitemapRoutes,
  },
  build: {
    transpile: ['epic-spinners'],
    // html: {
    //   minify: {
    //     collapseWhitespace: true,
    //     removeComments: true,
    //   },
    // },
    // postcss: {
    //   plugins: {
    //     tailwindcss: {},
    //     autoprefixer: {},
    //   },
    // },
  },
  loading: false,
  publicRuntimeConfig: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    nodeEnv: process.env.NODE_ENV || 'development',
  },
})
