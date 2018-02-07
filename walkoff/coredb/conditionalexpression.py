import logging
from sqlalchemy import Column, ForeignKey, Enum, orm
from sqlalchemy.orm import relationship, backref

from walkoff.coredb import Device_Base
from walkoff.coredb.executionelement import ExecutionElement
from walkoff.dbtypes import Guid

logger = logging.getLogger(__name__)


class ConditionalExpression(ExecutionElement, Device_Base):
    __tablename__ = 'conditional_expression'
    _action_id = Column(Guid(), ForeignKey('action.id'))
    _branch_id = Column(Guid(), ForeignKey('branch.id'))
    _parent_id = Column(Guid(), ForeignKey('conditional_expression.id'))
    operator = Column(Enum('truth', 'not', 'and', 'or', 'xor', name='operator_types'))
    child_expressions = relationship('ConditionalExpression',
                                     backref=backref('parent', remote_side='ConditionalExpression.id'),
                                     cascade='all, delete-orphan')
    conditions = relationship('Condition', backref=backref('_expression'), cascade='all, delete-orphan')

    def __init__(self, operator, id=None, child_expressions=None, conditions=None):
        ExecutionElement.__init__(self, id)
        self.operator = operator
        self.child_expressions = child_expressions if child_expressions is not None else []
        self.conditions = conditions if conditions is not None else []
        self.__operator_lookup = {'and': self._and,
                                  'or': self._or,
                                  'xor': self._xor,
                                  'truth': self._truth,
                                  'not': self._not}

    @orm.reconstructor
    def init_on_load(self):
        self.__operator_lookup = {'and': self._and,
                                  'or': self._or,
                                  'xor': self._xor,
                                  'truth': self._truth,
                                  'not': self._not}

    def execute(self, data_in, accumulator):
        self.__operator_lookup[self.operator](data_in, accumulator)

    def _and(self, data_in, accumulator):
        return self.__and_or(all, data_in, accumulator)

    def _or(self, data_in, accumulator):
        return self.__and_or(any, data_in, accumulator)

    def __and_or(self, operator, data_in, accumulator):
        return (operator(condition.execute(data_in, accumulator) for condition in self.conditions)
                and operator(expression.execute(data_in, accumulator) for expression in self.child_expressions))

    def _xor(self, data_in, accumulator):
        is_found = False
        for condition in self.conditions:
            if condition.execute(data_in, accumulator):
                if is_found:
                    return False
                is_found = True
        for expression in self.child_expressions:
            if expression.execute(data_in, accumulator):
                if is_found:
                    return False
                is_found = True
        return is_found

    def __get_single_target(self):
        return self.conditions[0] if self.conditions else self.child_expressions[0]

    def _truth(self, data_in, accumulator):
        return self.__get_single_target().execute(data_in, accumulator)

    def _not(self, data_in, accumulator):
        return not self.__get_single_target().execute(data_in, accumulator)
