// src/app/app.module.ts
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { OpenaiModule } from '../openai/openai.module';
import { BotModule } from '../bot/bot.module';

@Module({
  imports: [
    // 1️⃣ load .env and register ConfigService globally
    ConfigModule.forRoot({ isGlobal: true }),

    // 2️⃣ import the global OpenaiModule
    OpenaiModule,

    // 3️⃣ your bot logic (uses OpenaiService)
    BotModule,
  ],
})
export class AppModule {}
