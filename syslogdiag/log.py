from copy import copy
import datetime

from sysdata.mongodb.mongo_connection import mongoConnection, MONGO_ID_KEY
from syscore.dateutils import long_to_datetime, datetime_to_long
from syslogdiag.emailing import send_mail_msg


class logger(object):
    """
    log: used for writing messages

    Messages are datestamped, and tagged with attributes for storage / processing

    This is the base class

    Will also do reporting and emailing of errors


    """

    def __init__(self, type, log_level="Off", **kwargs):
        """
        Base class for logging.

        >>> log=logger("base_system") ## set up a logger with type "base_system"
        >>> log
        Logger (off) attributes- type: base_system
        >>>
        >>> log=logger("another_system", stage="test") ## optionally add other attributes
        >>> log
        Logger (off) attributes- stage: test, type: another_system
        >>>
        >>> log2=logger(log, log_level="on", stage="combForecast") ## creates a copy of log
        >>> log
        Logger (off) attributes- stage: test, type: another_system
        >>> log2
        Logger (on) attributes- stage: combForecast, type: another_system
        >>>
        >>> log3=log2.setup(stage="test2") ## to avoid retyping; will make a copy so attributes aren't kept
        >>> log2
        Logger (on) attributes- stage: combForecast, type: another_system
        >>> log3
        Logger (on) attributes- stage: test2, type: another_system
        >>>
        >>> log3.label(instrument_code="EDOLLAR") ## adds the attribute without making a copy
        >>> log3
        Logger (on) attributes- instrument_code: EDOLLAR, stage: test2, type: another_system
        >>>
        >>>
        """

        if isinstance(type, str):
            # been passed a label, so not inheriting anything
            log_attributes = dict(type=type)
            other_attributes = kwargs

            log_attributes = get_update_attributes_list(
                log_attributes, other_attributes)

        elif hasattr(type, "attributes"):
            # probably a log
            new_attributes = kwargs
            parent_attributes = type.attributes

            log_attributes = get_update_attributes_list(
                parent_attributes, new_attributes)

        else:
            raise Exception(
                "Can only create a logger from another logger, or a str identifier"
            )

        setattr(self, "attributes", log_attributes)
        self.set_logging_level(log_level)

    def logging_level(self):
        return getattr(self, "_log_level", "Off")

    def set_logging_level(self, new_level):
        new_level = new_level.lower()
        allowed_levels = ["off", "terse", "on"]

        if new_level not in allowed_levels:
            raise Exception("You can't log with level %s", new_level)

        setattr(self, "_log_level", new_level)

    def __repr__(self):
        attributes = self.attributes
        attr_keys = sorted(attributes.keys())

        attribute_desc = [
            keyname + ": " + str(attributes[keyname]) for keyname in attr_keys
        ]
        return "Logger (%s) attributes- %s" % (self._log_level,
                                               ", ".join(attribute_desc))

    def setup(self, **kwargs):

        new_log = copy(self)

        log_attributes = new_log.attributes
        passed_attributes = kwargs

        new_attributes = get_update_attributes_list(log_attributes,
                                                    passed_attributes)

        setattr(new_log, "attributes", new_attributes)
        setattr(new_log, "_log_level", self.logging_level())

        return new_log

    def label(self, **kwargs):
        log_attributes = self.attributes
        passed_attributes = kwargs

        new_attributes = get_update_attributes_list(log_attributes,
                                                    passed_attributes)

        setattr(self, "attributes", new_attributes)

    def msg(self, text, **kwargs):
        return self.log(text, msglevel=0, **kwargs)

    def terse(self, text, **kwargs):
        return self.log(text, msglevel=1, **kwargs)

    def warn(self, text, **kwargs):
        return self.log(text, msglevel=2, **kwargs)

    def error(self, text, **kwargs):
        return self.log(text, msglevel=3, **kwargs)

    def critical(self, text, **kwargs):
        return self.log(text, msglevel=4, **kwargs)

    def get_last_used_log_id(self):
        """
        Get last log id used. This should be stored in the underlying database.

        If no last log id, return None

        :return: int
        """
        raise NotImplementedError("You need to implement this method in an inherited class or use an inherited claass eg logToMongod")

    def update_log_id(self):
        """
        Update the current stored log id

        :return: None
        """
        raise NotImplementedError("You need to implement this method in an inherited class or use an inherited claass eg logToMongod")


    def get_next_log_id(self):
        """
        Get next log id

        :return: int
        """
        last_id = self.get_last_used_log_id()
        if last_id is None:
            last_id = -1

        next_id = last_id+1

        self.update_log_id(next_id)

        return next_id

    def log(self, text, msglevel=0, **kwargs):
        log_attributes = self.attributes
        passed_attributes = kwargs

        log_id = self.get_next_log_id()
        use_attributes = get_update_attributes_list(log_attributes,
                                                    passed_attributes)

        return self.log_handle_caller(msglevel, text, use_attributes, log_id)

    def log_handle_caller(self, msglevel, text, use_attributes, log_id):
        raise Exception(
            "You're using a base class for logger - you need to use an inherited class like logtoscreen()"
        )

    """
    Following two methods implement context manager
    """
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass



def get_update_attributes_list(parent_attributes, new_attributes):
    """
    Merge these two dicts together
    """

    joined_attributes = copy(parent_attributes)
    for keyname in new_attributes.keys():
        joined_attributes[keyname] = new_attributes[keyname]

    return joined_attributes


class logtoscreen(logger):
    """
    Currently reports to stdout

    In future versions will print to log files and databases

    Will also do proper error handling

    """

    def log_handle_caller(self, msglevel, text, use_attributes, log_id_NOT_USED):
        """
        >>> log=logtoscreen("base_system", log_level="off") ## this won't do anything
        >>> log.log("this wont print")
        >>> log.terse("nor this")
        >>> log.warn("this will")
        this will
        >>> log.error("and this")
        and this
        >>> log=logtoscreen(log, log_level="terse")
        >>> log.msg("this wont print")
        >>> log.terse("this will")
        this will
        >>> log=logtoscreen(log_level="on")
        >>> log.msg("now prints every little thing")
        now prints every little thing
        """
        log_level = self.logging_level()

        if msglevel == 0:
            if log_level == "on":
                print(text)
                # otherwise do nothing - either terse or off

        elif msglevel == 1:
            if log_level in ["on", "terse"]:
                print(text)
                # otherwise do nothing - either terse or off
        else:
            print(text)

        if msglevel == 2:
            print(text)

        if msglevel == 3:
            print(text)

        if msglevel == 4:
            raise Exception(text)

    def get_last_used_log_id(self):
        return getattr(self, "_log_id", None)

    def update_log_id(self, log_id):
        self._log_id = log_id

MSG_LEVEL_DICT = dict(m0="", m1="", m2="[Warning]", m3="[Error]", m4="*CRITICAL*")
TEXTMSG_LEVEL_DICT = {"": 0, }

LEVEL_ID = "_Level" #use underscores so less chance of a conflict with labels used by users
TIMESTAMP_ID = "_Timestamp"
TEXT_ID = "_Text"
LOG_RECORD_ID ="_Log_Record_id"

class logEntry(object):
    """
    Abstraction for database log entries
    """
    def __init__(self, text, log_timestamp = None, msglevel=0, input_attributes={}, log_id=0):

        use_attributes = copy(input_attributes)
        log_dict = copy(use_attributes)

        msg_level_text = MSG_LEVEL_DICT["m%d" % msglevel]

        if log_timestamp is None:
            log_timestamp = datetime.datetime.now()
        log_timestamp_aslong = datetime_to_long(log_timestamp)

        log_dict[LEVEL_ID] = msglevel
        log_dict[TIMESTAMP_ID] = log_timestamp_aslong
        log_dict[TEXT_ID] = text
        log_dict[LOG_RECORD_ID] = log_id

        self._log_dict = log_dict

        self._use_attributes = use_attributes
        self._text = text
        self._msglevel = msglevel
        self._msglevel_text = msg_level_text
        self._timestamp_as_long = log_timestamp_aslong
        self._timestamp = log_timestamp
        self._log_id = log_id

    @classmethod
    def log_entry_from_dict(logEntry, log_dict_input):
        """
        Starting with the dictionary representation, recover the original logEntry

        :param log_dict: dict, as per logEntry.log_dict()
        :return: logEntry object
        """
        log_dict = copy(log_dict_input)
        log_dict.pop(MONGO_ID_KEY)
        log_timestamp_aslong = log_dict.pop(TIMESTAMP_ID)
        msg_level = log_dict.pop(LEVEL_ID)
        text = log_dict.pop(TEXT_ID)
        log_id = log_dict.pop(LOG_RECORD_ID)
        input_attributes = log_dict

        log_timestamp = long_to_datetime(log_timestamp_aslong)

        log_entry = logEntry(text, log_timestamp=log_timestamp,
                             msglevel=msg_level, input_attributes=input_attributes, log_id=log_id)

        return log_entry

    def __repr__(self):
        return "%s %s %s %s" % (self._timestamp.strftime("%Y-%m-%d:%H%M.%S"),
                                str(self._use_attributes), self._msglevel_text, self._text)

    def log_dict(self):
        return self._log_dict


LOG_COLLECTION_NAME = "Logs"
EMAIL_ON_LOG_LEVEL = [4]

class logToMongod(logger):
    """
    Logs to a mongodb

    """
    def __init__(self, type, mongo_db = None, log_level="Off", **kwargs):
        self._mongo = mongoConnection(LOG_COLLECTION_NAME, mongo_db=mongo_db)

        super().__init__(type= type, log_level = log_level, ** kwargs)

        # this won't create the index if it already exists
        self._mongo.create_multikey_index(LOG_RECORD_ID, LEVEL_ID)

    def get_last_used_log_id(self):
        """
        Get last used log id. Returns None if not present

        :return: int or None
        """
        attribute_dict = dict(_meta_data="log_id")
        last_id_dict=self._mongo.collection.find_one(attribute_dict)
        if last_id_dict is None:
            return None
        return last_id_dict['next_id']

    def update_log_id(self, next_id):
        attribute_dict = dict(_meta_data="log_id")
        next_id_dict = dict(_meta_data="log_id", next_id=next_id)
        self._mongo.collection.replace_one(attribute_dict, next_id_dict, True)

        return None

    def log_handle_caller(self, msglevel, text, input_attributes, log_id):
        """
        Ignores log_level - logs everything, just in case

        Doesn't raise exceptions

        """
        log_entry = logEntry(text, msglevel=msglevel, input_attributes=input_attributes, log_id=log_id)
        print(log_entry)

        self._mongo.collection.insert_one(log_entry.log_dict())

        if msglevel in EMAIL_ON_LOG_LEVEL:
            ## Critical, send an email
            self.email_user(log_entry)

        return log_entry

    def email_user(self, log_entry):
        try:
            send_mail_msg(str(log_entry), "*CRITICAL ERROR*")
        except:
            self.error("Couldn't email user")



class accessLogFromMongodb(object):

    def __init__(self, mongo_db=None):
        self._mongo = mongoConnection(LOG_COLLECTION_NAME, mongo_db=mongo_db)

    def get_log_items(self, attribute_dict=dict(), lookback_days=1):
        """
        Return log items as list of text

        :param attribute_dict: dictionary of attributes to return logs for
        :return: list of str
        """

        results = self.get_log_items_as_entries(attribute_dict, lookback_days=lookback_days)

        # jam together as text
        results_as_text = [str(log_entry) for log_entry in results]

        return results_as_text

    def print_log_items(self, attribute_dict=dict(), lookback_days=1):
        """
        Print log items as list of text

        :param attribute_dict: dictionary of attributes to return logs for
        :return: list of str
        """

        results_as_text = self.get_log_items(attribute_dict=attribute_dict, lookback_days=lookback_days)
        print("\n".join(results_as_text))

    def get_log_items_as_entries(self, attribute_dict=dict(), lookback_days=1):
        """
        Return log items not as text, good for diagnostics

        :param attribute_dict: dictionary of attributes to return logs for
        :return: list of 4-typles: timestamp, level, text, attributes
        """

        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=lookback_days)
        timestamp_dict = {}
        timestamp_dict["$gt"] = datetime_to_long(cutoff_date)
        attribute_dict[TIMESTAMP_ID] = timestamp_dict

        result_dict = self._mongo.collection.find(attribute_dict)
        # from cursor to list...
        results_list = [single_log_dict for single_log_dict in result_dict]

        # ... to list of log entries
        results = [logEntry.log_entry_from_dict(single_log_dict)
                                           for single_log_dict in results_list]

        # sort by log ID
        results.sort(key=lambda x: x._log_id)

        return results


    def delete_log_items_from_before_n_days(self, days=365):
        # need something to delete old log records, eg more than x months ago

        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        attribute_dict={}
        timestamp_dict = {}
        timestamp_dict["$lt"] = datetime_to_long(cutoff_date)
        attribute_dict[TIMESTAMP_ID] = timestamp_dict

        self._mongo.collection.remove(attribute_dict)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
