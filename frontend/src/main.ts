import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';

bootstrapApplication(AppComponent, appConfig).catch((err) => {
  // Top-level bootstrap error handler; consider reporting to error service
  // eslint-disable-next-line no-console
  console.error('Bootstrap failed:', err);
});
