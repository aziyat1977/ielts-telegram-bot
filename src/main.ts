import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app/app.module';
import { ConfigService } from '@nestjs/config';
import express from 'express';

async function bootstrap() {
  // Create Nest application
  const app = await NestFactory.create(AppModule);

  // (Optional) start a separate Express server
  const expressApp = express();
  expressApp.get('/', (_req, res) => res.send('Nest is running'));
  expressApp.listen(3000, () =>
    console.log('Express listening on http://localhost:3000'),
  );

  // Retrieve your SYSTEM_PROMPT from env via ConfigService
  const configService = app.get(ConfigService);
  const systemPrompt = configService.get<string>('SYSTEM_PROMPT');
  console.log('SYSTEM_PROMPT:', systemPrompt);

  // No more app.set(...) here

  await app.listen(3001, () =>
    console.log('Nest listening on http://localhost:3001'),
  );
}

bootstrap();
