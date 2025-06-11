/* src/main.ts -------------------------------------------------------------- */
import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app/app.module';

import { readFileSync } from 'fs';
import { resolve } from 'path';
import { ConfigService } from '@nestjs/config';

async function bootstrap() {
  /* 1. Create Nest app (Express is used internally) */
  const app = await NestFactory.create(AppModule, { cors: true });

  /* 2. Global request validation / transformation */
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,          // strip unknown fields
      transform: true,          // auto-transform primitives ↔︎ DTO types
      forbidNonWhitelisted: true
    })
  );

  /* 3. Health-check / ping */
  app.getHttpAdapter()
     .getInstance()
     .get('/', (_req: any, res: any) =>
        res.send('IELTS-Telegram-Bot backend is live ✔️')
     );

  /* 4. Load examiner SYSTEM_PROMPT once and expose it app-wide */
  const systemPromptPath = resolve(__dirname, '..', 'prompts', 'system.txt');
  const systemPrompt = readFileSync(systemPromptPath, 'utf8');
  app.set('SYSTEM_PROMPT', systemPrompt);

  /* 5. Port from env or fallback */
  const cfg = app.get(ConfigService);
  const port = Number(cfg.get('PORT')) || 3000;

  await app.listen(port);
  console.log(`🚀  Nest is listening on http://localhost:${port}`);
}

/* graceful bootstrap */
bootstrap().catch(err => {
  console.error('❌  Bootstrap failed:', err);
  process.exit(1);
});
/* ------------------------------------------------------------------------- */
