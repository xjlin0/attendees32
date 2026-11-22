import { defineConfig, Plugin } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

// Plugin to eliminate DevExtreme's legacy 'unload' event listener in DataGrid stateStoring,
// replacing it with modern 'pagehide' to avoid Permissions-Policy violations.
function eliminateUnloadPlugin(): Plugin {
  return {
    name: 'eliminate-unload-plugin',
    transform(code: string, id: string) {
      if (id.includes('state_storing') || id.includes('m_state_storing_core')) {
        return {
          code: code.replace(/"unload"/g, '"pagehide"'),
          map: null,
        };
      }
    },
  };
}

export default defineConfig({
  base: '/static/',
  plugins: [vue(), eliminateUnloadPlugin()],
  resolve: {
    alias: {
      vue: 'vue/dist/vue.esm-bundler.js',
    },
  },
  server: {
    watch: {
      usePolling: true,
      interval: 1000,
    },
  },
  build: {
    outDir: resolve(__dirname, 'attendees/static'),
    emptyOutDir: false,
    rollupOptions: {
      input: {
        rosters: resolve(__dirname, 'attendees/frontend/rosters/main.ts'),
        // Add new pages here in the future, e.g.:
        // gatherings: resolve(__dirname, 'attendees/frontend/gatherings/main.ts'),
        // attendances: resolve(__dirname, 'attendees/frontend/attendances/main.ts'),
      },
      output: {
        entryFileNames: 'js/bundles/[name].bundle.js',
        chunkFileNames: 'js/bundles/chunks/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith('.css')) {
            return 'css/bundles/[name].bundle[extname]';
          }
          if (/\.(woff2?|ttf|eot)$/.test(assetInfo.name || '')) {
            return 'fonts/[name][extname]';
          }
          return 'assets/[name]-[hash][extname]';
        },
        format: 'es',
      },
    },
  },
  define: {
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'production'),
  },
});
