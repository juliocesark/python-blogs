from concurrent.futures import ThreadPoolExecutor, TimeoutError

from django.utils import timezone
from django.core.management.base import BaseCommand

import gsoc.settings as config
from gsoc.models import Scheduler, GsocYear, UserProfile, Builder
from gsoc.common.utils import commands, build_tasks


class Command(BaseCommand):
    help = 'Run the cron command to process items such as sending scheduled emails etc.'
    tasks = ['build_items', 'process_items']
    requires_system_checks = False   # for debugging

    # cleanup sessions
    # Session.objects.all().delete()

    def add_arguments(self, parser):
        parser.add_argument(
            'task',
            nargs='?',
            choices=self.tasks,
            type=str,
            help='The task which will be started'
            )
        parser.add_argument(
            '-t',
            '--timeout',
            nargs='?',
            default=config.RUNCRON_TIMEOUT,
            type=int,
            help='Set timeout'
            )
        parser.add_argument(
            '-n',
            '--num_workers',
            nargs='?',
            default=config.RUNCRON_NUM_WORKERS,
            type=int,
            help='Set number of workers'
            )

    def build_items(self, options):
        # build tasks
        today = timezone.now()
        x = Builder.objects.filter(built=False, activation_date=None).all()
        y = Builder.objects.filter(built=False, activation_date__lte=today).all()
        builders = x | y

        if len(builders) is 0:
            self.stdout.write(self.style.SUCCESS('No build tasks'), ending='\n')
        else:
            for builder in builders:
                self.stdout.write('Running build task {}:{}'
                                  .format(builder.category, builder.pk), ending='\n')
                getattr(build_tasks, builder.category)(builder)
                self.stdout.write(self.style
                                  .SUCCESS('Finished build task {}:{}'
                                           .format(builder.category, builder.pk)),
                                  ending='\n')
                builder.built = True
                builder.save()

    def handle_process(self, scheduler):
        self.stdout.write('Running command {}:{}'
                          .format(scheduler.command, scheduler.id), ending='\n')
        err = getattr(commands, scheduler.command)(scheduler)
        if not err:
            self.stdout.write(self.style
                              .SUCCESS('Finished command {}:{}'
                                       .format(scheduler.command, scheduler.id)),
                              ending='\n')
            scheduler.success = True
            scheduler.save()

        else:
            self.stdout.write(
                self.style.ERROR(
                    'Command {}:{} failed with error: {}' .format(
                        scheduler.command,
                        scheduler.id,
                        err)),
                ending='\n')
            scheduler.success = False
            scheduler.last_error = err
            scheduler.save()

    def process_items(self, options):
        # custom handlers
        irc_schedulers = Scheduler.objects.filter(success=None, command='send_irc_msg')
        if len(irc_schedulers) is 0:
            self.stdout.write(self.style.SUCCESS('No scheduled send_irc_msg tasks'), ending='\n')
        else:
            self.stdout.write(self.style.SUCCESS('Sending {} scheduled irc message(s)'
                                                 .format(len(irc_schedulers))), ending='\n')
            commands.send_irc_msgs(irc_schedulers)
            self.stdout.write(self.style.SUCCESS('Sent {} irc message(s)'
                                                 .format(len(irc_schedulers))), ending='\n')

        # generic handlers
        today = timezone.now()
        x = Scheduler.objects.filter(success=None, activation_date=None).all()
        y = Scheduler.objects.filter(success=None, activation_date__lte=today).all()
        schedulers = x | y

        threads = []
        if len(schedulers) is not 0:
            try:
                executor = ThreadPoolExecutor(max_workers=options['num_workers'])
                executor.map(self.handle_process, schedulers, timeout=options['timeout'])
            except TimeoutError as e:
                self.stdout.write(self.style.ERROR('Time limit exceeded'), ending='\n')

        else:
            self.stdout.write(self.style.SUCCESS('No more scheduled tasks'), ending='\n')

    def handle(self, *args, **options):
        if options['task']:
            getattr(self, options['task'])(options)
        else:
            self.build_items(options)
            self.process_items(options)
