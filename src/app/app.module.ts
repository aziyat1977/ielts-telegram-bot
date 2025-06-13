// src/app/app.module.ts
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { OpenaiModule } from '../openai/openai.module';
import { BotModule } from '../bot/bot.module';

@Module({
  imports: [
    // loads .env and makes ConfigService global
    ConfigModule.forRoot({ isGlobal: true }),

    // global OpenaiService provider
    OpenaiModule,

    // your bot functionality
    BotModule,
  ],
})
export class AppModule {}
