import { Module } from '@nestjs/common';
import { BotModule } from '../bot/bot.module';
import { OpenaiService } from '../openai/openai.service';

@Module({
  imports: [BotModule],
  providers: [OpenaiService],
  exports: [OpenaiService],
})
export class AppModule {}
