import { Module } from '@nestjs/common';
import { BotService } from './bot.service';
import { OpenaiService } from '../openai/openai.service';

@Module({
  providers: [BotService, OpenaiService],
})
export class BotModule {}
