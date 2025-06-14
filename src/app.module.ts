import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';

import { OpenaiModule } from './openai/openai.module';
import { BotModule } from './bot/bot.module';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }), // global config
    OpenaiModule,
    BotModule,
  ],
})
export class AppModule {}
