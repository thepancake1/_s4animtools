from _s4animtools.animation_importer.types.basic import uint32, float32, string
from _s4animtools.animation_importer.types.spatial import Vector3, Quaternion
from _s4animtools.animation_importer.structure.definition import Property
from _s4animtools.animation_importer.types.ik_configuration import SlotAssignment
from _s4animtools.animation_importer.types.event_list import ClipEvent


class Header():


    def deserialize(self, data):
        self.version = uint32.deserialize(data)
        self.flags = uint32.deserialize(data)
        self.duration = float32.deserialize(data)
        self.initialOffsetQ = Quaternion.deserialize(data)
        self.initialOffsetT = Vector3.deserialize(data)
        self.referenceNamespaceHash = uint32.deserialize(data)
        self.surfaceNamespaceHash = uint32.deserialize(data)
        self.surfaceJointNameHash = uint32.deserialize(data)
        self.surfaceChildNamespaceHash = uint32.deserialize(data)
        self.clipNameLength, self.clipName = string.deserialize(data)
        self.rigNameLength, self.rigName = string.deserialize(data)
        self.explicitNamespaceCount = uint32.deserialize(data)
        self.explicitNamespaces = []
        for i in range(self.explicitNamespaceCount):
            _, namespace = string().deserialize(data)
            self.explicitNamespaces.append(namespace)
        self.slotAssignmentCount = uint32.deserialize(data)
        self.slotAssignments = SlotAssignment.deserialize(data, self.slotAssignmentCount)
        self.clipEventCount = uint32.deserialize(data)
        self.clipEventList, parsed_events = ClipEvent.deserialize(self.clipName, data, self.clipEventCount, self.version)
        self.filler = uint32.deserialize(data)
        #if self.surfaceChildNamespaceHash != 2166136261:
        #    print(self.clipName, self.surfaceNamespaceHash)

        return self, self.clipName, parsed_events
       # print(vars(self))

