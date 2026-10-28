import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.nival.chitbook',
  appName: 'ChitBook',
  webDir: 'dist',
  server: {
    androidScheme: 'http'
  }
};

export default config;
