from multiprocessing import Queue
from model import SRMission, Session, SRMissionStatus, Torrent, TorrentType
from sr_mission import RealWaifuUpScaler, UpScalerMission
import threading
import config
from time import sleep
import datetime
import config
from notification import sendNotificationFinish, sendNotificationWarning

def SuperResolutionFinished(torrent_id: int):
    with Session() as session:
        torrent = session.query(Torrent).filter_by(id=torrent_id).first()
        if torrent is None:
            return
        sr_mission = torrent.super_resolution_mission
        if sr_mission is None:
            return
        type_name = ""
        if torrent.torrent_type == TorrentType.TV:
            type_name = "TV"
        elif torrent.torrent_type == TorrentType.MOVIE:
            type_name = "Movie"
        else:
            type_name = "Bangumi"
        if sr_mission.status == SRMissionStatus.DONE:
            sendNotificationFinish(type_name, sr_mission.output_file, 'super_resolution', sr_mission.output_file)
        else:
            sendNotificationWarning(type_name, sr_mission.output_file, 'super_resolution', sr_mission.error_info)

model = RealWaifuUpScaler(config.sr_scale, config.sr_model_path, config.sr_half, config.sr_device)
def UpScalerMissionWrapper(mission_id):
    try:
        with Session() as session:
            mission = session.query(SRMission).filter(SRMission.id == mission_id).first()
            mission.start_time = datetime.datetime.now()
            session.commit()
            upscaler = UpScalerMission(
                num_thread  =   config.sr_num_thread,
                scale       =   config.sr_scale,
                model       =   model,
                tile        =   config.sr_tile,
                cache_mode  =   config.sr_cache_mode,
                alpha       =   config.sr_alpha,
                encoder     =   mission.encoder,
                inp_file    =   mission.input_file,
                out_file    =   mission.output_file
            )
            result = None
            def run_upscaler():
                try:
                    upscaler.start()
                except Exception as e:
                    global result
                    print(str(e))
                    result = e
            thread = threading.Thread(target=run_upscaler)
            thread.start()
            while thread.is_alive():
                mission = session.query(SRMission).filter(SRMission.id == mission_id).first()
                enc_prog, super_prog = upscaler.getProgress()
                mission.progress_encode = enc_prog
                mission.progress_super_resolution = super_prog
                session.commit()
                sleep(5)
            thread.join()
            if result is not None:
                raise result
        with Session() as session:
            mission = session.query(SRMission).filter(SRMission.id == mission_id).first()
            mission.encode_duration_ms = upscaler.total_encoded_time_ms
            mission.super_resolution_duration_ms = upscaler.total_super_resolution_time_ms
            mission.status = SRMissionStatus.DONE
            mission.end_time = datetime.datetime.now()
            session.commit()
            SuperResolutionFinished(mission.torrent_id)
    except Exception as e:
        with Session() as session:
            mission = session.query(SRMission).filter(SRMission.id == mission_id).first()
            mission.error_info = str(e)
            mission.end_time = datetime.datetime.now()
            mission.status = SRMissionStatus.ERROR
            session.commit()
            SuperResolutionFinished(mission.torrent_id)
    return True

class MissionManager(threading.Thread):
    def __init__(self):
        super(MissionManager, self).__init__()
        self.missions = []
        self.mission_queue = Queue()
        self.is_finished = False
    
        with Session() as session:
            # Mark all processing missions as error
            processing_missions = session.query(SRMission).filter(SRMission.status == SRMissionStatus.PROCESSING).all()
            for mission in processing_missions:
                mission.status = SRMissionStatus.ERROR
                mission.end_time = datetime.datetime.now()
                mission.error_info = "Unexpected shutdown"
                session.commit()
                SuperResolutionFinished(mission.torrent_id)

            # Start all pending missions
            pending_missions = session.query(SRMission).filter(SRMission.status == SRMissionStatus.PENDING).all()
            for mission in pending_missions:
                self.add_mission(mission.id)

    def add_mission(self, torrent_id, inp_file, out_file, encoder):
        with Session() as session:
            old_missions = session.query(SRMission).filter(SRMission.torrent_id == torrent_id).all()
            has_pending_mission = False
            for old_mission in old_missions:
                if old_mission.status == SRMissionStatus.PENDING:
                    has_pending_mission = True
                else:
                    session.delete(old_mission)
                    session.commit()
            if has_pending_mission:
                return

            mission = SRMission(
                torrent_id = torrent_id,
                input_file = inp_file,
                output_file = out_file,
                encoder = encoder,
                status = SRMissionStatus.PENDING
            )
            session.add(mission)
            session.commit()
            session.refresh(mission)
            self.mission_queue.put(mission.id)
    
    def stop(self):
        self.is_finished = True

    def run(self):
        while not self.is_finished:
            try:
                mission_id = self.mission_queue.get(timeout=1)
            except: # Queue.Empty
                mission_id = None
            mission_thread = None
            if mission_id is not None:
                with Session() as session:
                    mission = session.query(SRMission).filter(SRMission.id == mission_id).first()
                    mission.status = SRMissionStatus.PROCESSING
                    mission_thread = threading.Thread(target=UpScalerMissionWrapper, args=(mission_id,))
                    session.commit()
            if mission_thread is not None:
                mission_thread.start()
                while not self.is_finished:
                    if not mission_thread.is_alive():
                        mission_thread.join()
                        break
                    sleep(5)

mission_manager : MissionManager = MissionManager()

def startSRMissionManager():
    mission_manager.start()

def stopSRMissionManager():
    mission_manager.stop()
    mission_manager.join()