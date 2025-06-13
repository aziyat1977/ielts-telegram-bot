import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { BotModule } from '../bot/bot.module';
import { OpenaiModule } from '../openai/openai.module';

@Module({
  imports: [
    // 1) Load .env and make ConfigService available everywhere
    ConfigModule.forRoot({ isGlobal: true }),
    // 2) Your feature modules
    OpenaiModule,
    BotModule,
  ],
})
export class AppModule {}
